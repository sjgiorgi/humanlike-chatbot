import base64
import io
import json
import logging
import os
from datetime import datetime

import openai
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
    # image_vector = Image.open(file)
    try:
        image_vector = file
        square_image = make_square(image_vector)

        image_bytes_io = io.BytesIO()
        square_image.save(image_bytes_io, format="PNG")
        image_bytes_io.seek(0)

        image_file = ("image.png", image_bytes_io, "image/png")

        openai.api_key = os.getenv("OPENAI_API_KEY")
        client = openai.OpenAI()
        response = client.images.edit(
            model="gpt-image-1",
            image=[image_file],
            prompt=os.getenv("CHATBOT_AVATAR_PROMPT"),
        )
        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        image = ContentFile(image_bytes)
        # Timestamp to help make image name unique, avoids overwriting images
        return (
            image,
            f"{bot_name}_{avatar_type}_{conversation_id if conversation_id else ''}_{int(datetime.now().timestamp())!s}.png",
        )
    except Exception as e:
        logger.exception(f"[ERROR] {e}")
        return None


@method_decorator(csrf_exempt, name="dispatch")
class AvatarAPIView(View):
    def get(self, request, *args, **kwargs):
        try:
            avatars = Avatar.objects.values("bot")
            return JsonResponse({"avatars": list(avatars)}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            bot_name = data.get("bot_name")
            bot = Bot.objects.get(name=bot_name)
            conversation_id = data.get("conversation_id")
            image_url = data.get("image_path")
            image_key = None

            if bot.avatar_type == "default":
                image, image_key = generate_avatar(
                    # request.FILES.get("image"),
                    download("uploads", image_url),
                    bot_name,
                    bot.avatar_type,
                )
                upload(image, image_key)
                delete("uploads", image_url)
                Avatar.objects.create(
                    bot=bot,
                    bot_conversation=conversation_id,
                    chatbot_avatar=image_key,
                )
            if bot.avatar_type == "user" and conversation_id:
                image, image_key = generate_avatar(
                    download("uploads", image_url),
                    bot_name,
                    bot.avatar_type,
                    conversation_id,
                )
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
            return JsonResponse({"error": "Bot not found"}, status=404)

        try:
            image_key = None

            if avatar.chatbot_avatar:
                delete("avatar", avatar.chatbot_avatar)

            if bot.avatar_type == "default":
                data = json.loads(request.body)
                image_url = data.get("image_path")
                edit_image, image_key = generate_avatar(
                    download("uploads", image_url),
                    bot.name,
                    bot.avatar_type,
                )
                upload(edit_image, image_key)
                delete("uploads", image_url)

            avatar.bot = bot
            avatar.chatbot_avatar = image_key
            avatar.save()

            return JsonResponse({"message": "Avatar updated successfully."}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
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
