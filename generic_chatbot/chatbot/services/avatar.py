import base64
import io
import json
import logging
import os
import time
from datetime import datetime

import openai
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from PIL import Image

from ..models import Avatar, Bot
from .s3_helper import delete, download, get_presigned_url, get_random_image, upload

logger = logging.getLogger(__name__)


def make_square(image, fill_color=(255, 255, 255, 0)):
    """
    Pads the image to make it square.
    fill_color: default is transparent; can change to white (255,255,255) if needed.
    """
    x, y = image.size
    size = max(x, y)
    new_image = Image.new("RGBA", (size, size), fill_color)
    new_image.paste(image, ((size - x) // 2, (size - y) // 2))
    return new_image.resize((512, 512))


def generate_avatar(file, bot_name, avatar_type, conversation_id=None):
    try:
        # Handle both PIL Image objects and Django UploadedFile objects
        if hasattr(file, "read"):
            # Django UploadedFile object
            image_vector = Image.open(file)
        else:
            # PIL Image object
            image_vector = file
        square_image = make_square(image_vector)

        image_bytes_io = io.BytesIO()
        square_image.save(image_bytes_io, format="PNG")
        image_bytes_io.seek(0)

        # Create a proper file-like object with correct MIME type
        image_file = ("image.png", image_bytes_io, "image/png")

        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.error("[ERROR] OPENAI_API_KEY not set")
            return None, None
            
        client = openai.OpenAI()
        
        chatbot_avatar_prompt = os.getenv("CHATBOT_AVATAR_PROMPT")
        if not chatbot_avatar_prompt:
            logger.error("[ERROR] CHATBOT_AVATAR_PROMPT not set")
            return None, None
            
        try:
            response = client.images.edit(
                model="gpt-image-1",
                image=[image_file],  # Pass as list as in original
                prompt="Create a fun and friendly bitmoji-style avatar based on this person's image. Capture the main facial features like hair style, eye shape, and skin tone, but simplify and stylize them with smooth lines and bright colors. The avatar should look cartoonish, approachable, and suitable as a profile picture. The output image's size should be square",
            )
            
            # Check if response has data
            if not response.data or len(response.data) == 0:
                logger.error("[ERROR] OpenAI API returned no data")
                return None, None
                
            image_data = response.data[0]
            
            # Handle both b64_json and url responses
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                # Legacy format - base64 encoded image
                image_base64 = image_data.b64_json
                image_bytes = base64.b64decode(image_base64)
                image = ContentFile(image_bytes)
            elif hasattr(image_data, "url") and image_data.url:
                # New format - download image from URL
                logger.info(f"[DEBUG] Downloading image from URL: {image_data.url}")
                try:
                    response = requests.get(image_data.url, timeout=30)
                    response.raise_for_status()
                    image_bytes = response.content
                    image = ContentFile(image_bytes)
                except Exception as e:
                    logger.error(f"[ERROR] Failed to download image from URL: {e}")
                    return None, None
            else:
                logger.error("[ERROR] OpenAI API response missing both b64_json and url fields")
                return None, None
        except Exception as e:
            logger.exception(f"[ERROR] OpenAI API call failed: {e}")
            return None, None
            
        # Set the image name with timestamp to make it unique
        image.name = f"{bot_name}_{avatar_type}_{conversation_id if conversation_id else ''}_{int(datetime.now().timestamp())!s}_avatar.png"
        
        return image
    except Exception as e:
        logger.exception(f"[ERROR] {e}")
        return None, None


@method_decorator(csrf_exempt, name="dispatch")
class AvatarAPIView(View):
    def get(self, request, *args, **kwargs):
        try:
            avatars = Avatar.objects.values("bot")
            return JsonResponse({"avatars": list(avatars)}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, *args, **kwargs):
        logger.info(f"[DEBUG] Avatar upload request received. Method: {request.method}, Content-Type: {request.content_type}")
        logger.info(f"[DEBUG] Request FILES: {list(request.FILES.keys()) if request.FILES else 'No files'}")
        logger.info(f"[DEBUG] Request POST: {list(request.POST.keys()) if request.POST else 'No POST data'}")
        
        try:
            # Check if this is a simple file upload (from EditBots)
            if request.FILES.get("image"):
                # Simple file upload from EditBots
                bot_name = request.POST.get("bot_name")
                if not bot_name:
                    return JsonResponse({"error": "bot_name is required"}, status=400)
                
                try:
                    bot = Bot.objects.get(name=bot_name)
                except Bot.DoesNotExist:
                    return JsonResponse({"error": f"Bot with name '{bot_name}' not found"}, status=404)
                
                image_file = request.FILES.get("image")
                
                # Generate avatar using the uploaded file
                try:
                    image = generate_avatar(
                        image_file,
                        bot_name,
                        bot.avatar_type,
                    )
                    if not image:
                        return JsonResponse({"error": "Failed to generate avatar"}, status=500)
                except Exception as e:
                    logger.exception(f"[ERROR] Avatar generation failed: {e}")
                    return JsonResponse({"error": f"Avatar generation failed: {e!s}"}, status=500)
                
                # Create avatar record - handle both model structures
                logger.info(f"[DEBUG] Backend environment: {settings.BACKEND_ENVIRONMENT}")
                
                if hasattr(Avatar, "image"):
                    # Main branch structure (ImageField)
                    avatar = Avatar.objects.create(
                        bot=bot,
                        bot_conversation=None,
                        image=image,
                    )
                else:
                    # Staging branch structure (S3 keys)
                    # For local development, save the file path
                    if settings.BACKEND_ENVIRONMENT == "local":
                        logger.info("[DEBUG] Using local environment - saving file path")
                        chatbot_avatar_key = image.name if hasattr(image, "name") else str(image)
                    else:
                        # For production, upload to S3
                        logger.info("[DEBUG] Using production environment - uploading to S3")
                        try:
                            s3_key = f"avatar/{bot_name}_{int(time.time())}.png"
                            # Reset the ContentFile to the beginning before uploading
                            image.seek(0)
                            upload(image, s3_key)
                            chatbot_avatar_key = s3_key
                        except Exception as e:
                            logger.exception(f"[ERROR] S3 upload failed: {e}")
                            # Fallback to local path if S3 fails
                            chatbot_avatar_key = image.name if hasattr(image, "name") else str(image)
                    
                    avatar = Avatar.objects.create(
                        bot=bot,
                        bot_conversation=None,
                        chatbot_avatar=chatbot_avatar_key,
                    )
                
                return JsonResponse(
                    {"message": "SUCCESS!"},
                    status=201,
                )
            
            # Original S3-based implementation
            data = json.loads(request.body)
            bot_name = data.get("bot_name")
            bot = Bot.objects.get(name=bot_name)
            conversation_id = data.get("conversation_id")
            image_url = data.get("image_path")
            image_key = None

            if bot.avatar_type == "default":
                image = generate_avatar(
                    # request.FILES.get("image"),
                    download("uploads", image_url),
                    bot_name,
                    bot.avatar_type,
                )
                image_key = image.name if hasattr(image, "name") else f"{bot_name}_{int(time.time())}.png"
                upload(image, image_key)
                delete("uploads", image_url)
                Avatar.objects.create(
                    bot=bot,
                    bot_conversation=conversation_id,
                    chatbot_avatar=image_key,
                )
            if bot.avatar_type == "user" and conversation_id:
                image = generate_avatar(
                    download("uploads", image_url),
                    bot_name,
                    bot.avatar_type,
                    conversation_id,
                )
                image_key = image.name if hasattr(image, "name") else f"{bot_name}_{int(time.time())}.png"
                upload(image, image_key)
                delete("uploads", image_url)
                Avatar.objects.create(
                    bot=bot,
                    bot_conversation=conversation_id,
                    participant_avatar=image_key,
                )

            logger.debug(f"[DEBUG] {bot.name}, {conversation_id}, {image_key}")
            return JsonResponse(
                {"message": "SUCCESS!"},
                status=200,
            )
        except Exception as e:
            logger.exception(f"[ERROR] {e}")
            return JsonResponse(
                {"message": "FAILED!"},
                status=500,
            )


@method_decorator(csrf_exempt, name="dispatch")
class AvatarDetailAPIView(View):
    def get(self, request, bot_name, *args, **kwargs):
        try:
            bot = Bot.objects.get(name=bot_name)
            data = {
                "bot_id": bot.pk,
                "bot_name": bot.name,
                "avatar_type": bot.avatar_type,
            }

            if bot.avatar_type == "user":
                conversation_id = request.GET.get("conversation_id")
                condition = request.GET.get("condition")  # Default: None
                source = request.GET.get("source")  # Default: None
                avatar = Avatar.objects.get(bot=bot, bot_conversation=conversation_id)

                if source == "qualtrics" and avatar is not None:
                    return JsonResponse({"status": True}, status=200)

                if condition == "control":
                    avatar.condition = "control"
                    avatar.chatbot_avatar = os.getenv("CHATBOT_CONTROL_IMAGE")
                elif condition == "dissimilar":
                    avatar.condition = "dissimilar"
                    if not avatar.chatbot_avatar:
                        avatar.chatbot_avatar = get_random_image(
                            "avatar", avatar.participant_avatar,
                        )
                else:
                    avatar.chatbot_avatar = avatar.participant_avatar
                avatar.save()
                
                if avatar.chatbot_avatar:
                    # Check if we're in local development
                    if os.getenv("BACKEND_ENVIRONMENT") == "local":
                        # For local development, serve from media directory
                        from django.conf import settings
                        local_path = os.path.join(settings.MEDIA_ROOT, "avatars", avatar.chatbot_avatar)
                        if os.path.exists(local_path):
                            data["image_url"] = f"/media/avatars/{avatar.chatbot_avatar}"
                        else:
                            data["image_url"] = None
                    else:
                        # Production: Get presigned URL
                        data["image_url"] = get_presigned_url("avatar", avatar.chatbot_avatar)
                else:
                    data["image_url"] = None
            elif bot.avatar_type == "default":
                try:
                    avatar = Avatar.objects.get(bot=bot, bot_conversation=None)
                    if avatar.chatbot_avatar:
                        # Check if we're in local development
                        if os.getenv("BACKEND_ENVIRONMENT") == "local":
                            # For local development, serve from media directory
                            from django.conf import settings
                            local_path = os.path.join(settings.MEDIA_ROOT, "avatars", avatar.chatbot_avatar)
                            if os.path.exists(local_path):
                                data["image_url"] = f"/media/avatars/{avatar.chatbot_avatar}"
                            else:
                                data["image_url"] = None
                        else:
                            # Production: Get presigned URL
                            data["image_url"] = get_presigned_url("avatar", avatar.chatbot_avatar)
                    else:
                        data["image_url"] = None
                except Avatar.DoesNotExist:
                    data["image_url"] = None
            else:  # avatar_type == "none"
                data["image_url"] = None
            return JsonResponse(data, status=200)
        except Bot.DoesNotExist:
            logger.exception("[ERROR] Bot not found")
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            logger.exception(f"[ERROR] {e}")
            return JsonResponse({"error": "Bot not found"}, status=404)

    def post(self, request, bot_name, *args, **kwargs):
        try:
            bot = Bot.objects.get(pk=int(bot_name))
            avatar = Avatar.objects.get(bot=bot, bot_conversation=None)
        except Bot.DoesNotExist:
            logger.error(f"[ERROR] Bot with pk={bot_name} not found")
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Avatar.DoesNotExist:
            logger.error(f"[ERROR] Avatar for bot pk={bot_name} not found")
            return JsonResponse({"error": "Avatar not found"}, status=404)

        try:
            # Check if this is a simple file upload (from EditBots)
            if request.FILES.get("image"):
                # Simple file upload from EditBots
                image_file = request.FILES.get("image")
                
                # Delete old avatar if exists (handle both image field and chatbot_avatar field)
                if hasattr(avatar, "image") and avatar.image:
                    avatar.image.delete(save=False)
                elif avatar.chatbot_avatar:
                    # Delete from S3 if it exists
                    try:
                        delete("avatar", avatar.chatbot_avatar)
                    except:
                        pass  # Ignore S3 errors in local development
                
                # Generate new avatar
                edit_image = generate_avatar(
                    image_file,
                    bot.name,
                    bot.avatar_type,
                )
                
                # Update avatar - handle both model structures
                logger.info(f"[DEBUG] Backend environment: {settings.BACKEND_ENVIRONMENT}")
                
                if hasattr(avatar, "image"):
                    # Main branch structure (ImageField)
                    avatar.image = edit_image
                # Staging branch structure (S3 keys)
                # For local development, save the file locally
                elif settings.BACKEND_ENVIRONMENT == "local":
                    logger.info("[DEBUG] Using local environment - saving file locally")
                    import os
                    
                    # Create media directory if it doesn't exist
                    media_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
                    os.makedirs(media_dir, exist_ok=True)
                    
                    # Get the filename from the image
                    image_key = edit_image.name if hasattr(edit_image, "name") else f"{bot.name}_{int(time.time())}.png"
                    
                    # Save the processed image locally
                    local_path = os.path.join(media_dir, image_key)
                    with open(local_path, "wb") as f:
                        f.write(edit_image.read())
                    
                    avatar.chatbot_avatar = image_key
                else:
                    # For production, upload to S3
                    logger.info("[DEBUG] Using production environment - uploading to S3")
                    try:
                        s3_key = f"avatar/{bot.name}_{int(time.time())}.png"
                        logger.info(f"[DEBUG] Attempting S3 upload with key: {s3_key}")
                        # Reset the ContentFile to the beginning before uploading
                        edit_image.seek(0)
                        upload_result = upload(edit_image, s3_key)
                        logger.info(f"[DEBUG] S3 upload result: {upload_result}")
                        if upload_result:
                            avatar.chatbot_avatar = s3_key
                            logger.info(f"[DEBUG] Avatar record updated with S3 key: {s3_key}")
                        else:
                            logger.error("[ERROR] S3 upload returned None")
                            raise Exception("S3 upload failed - returned None")
                    except Exception as e:
                        logger.exception(f"[ERROR] S3 upload failed: {e}")
                        # For production, we can't fallback to local storage
                        # Return error instead of saving invalid path
                        return JsonResponse({"error": f"Failed to upload avatar to S3: {e!s}"}, status=500)
                
                avatar.save()
                
                return JsonResponse({"message": "Avatar updated successfully."}, status=200)
            
            # Original S3-based implementation
            image_key = None

            if avatar.chatbot_avatar:
                delete("avatar", avatar.chatbot_avatar)

            if bot.avatar_type == "default":
                data = json.loads(request.body)
                image_url = data.get("image_path")
                edit_image = generate_avatar(
                    download("uploads", image_url),
                    bot.name,
                    bot.avatar_type,
                )
                image_key = edit_image.name if hasattr(edit_image, "name") else f"{bot.name}_{int(time.time())}.png"
                upload(edit_image, image_key)
                delete("uploads", image_url)

            avatar.bot = bot
            avatar.chatbot_avatar = image_key
            avatar.save()

            return JsonResponse({"message": "Avatar updated successfully."}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            logger.exception(f"[ERROR] AvatarDetailAPIView.post failed: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, bot_name, *args, **kwargs):
        try:
            avatars = Avatar.objects.filter(bot=Bot.objects.filter(pk=int(bot_name)))
            for avatar in avatars:
                if avatar.image_path:
                    delete("avatar", avatar.image_path)
            avatars.delete()
            return JsonResponse({"message": "Bot deleted successfully."}, status=204)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
