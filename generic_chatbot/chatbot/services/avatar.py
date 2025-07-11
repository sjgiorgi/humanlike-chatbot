import json
from datetime import datetime
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.core.files.base import ContentFile
from ..models import Bot, Avatar
import os
import io
import openai
from PIL import Image
import base64
from .s3_helper import download, upload, delete, get_presigned_url

import logging
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
        square_image.save(image_bytes_io, format='PNG')
        image_bytes_io.seek(0) 

        image_file = ("image.png", image_bytes_io, "image/png")

        openai.api_key = os.getenv("OPENAI_API_KEY")
        client = openai.OpenAI()
        response = client.images.edit(
            model="gpt-image-1",
            image=[image_file],
            prompt="Create a fun and friendly bitmoji-style avatar based on this person's image. Capture the main facial features like hair style, eye shape, and skin tone, but simplify and stylize them with smooth lines and bright colors. The avatar should look cartoonish, approachable, and suitable as a profile picture. The output image's size should be square",
        )
        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        image = ContentFile(image_bytes)
        # Timestamp to help make image name unique, avoids overwriting images
        return (
            image,
            f"{bot_name}_{avatar_type}_{conversation_id if conversation_id else ''}_{str(int(datetime.now().timestamp()))}.png"
        )
    except Exception as e:
        logger.exception(f'[ERROR] {e}')
        return None

@method_decorator(csrf_exempt, name='dispatch')
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
                    download('uploads', image_url),
                    bot_name,
                    bot.avatar_type
                )
                upload(image, image_key)
                delete('uploads', image_url)
            if bot.avatar_type == "user" and conversation_id:
                image, image_key = generate_avatar(
                    download('uploads', image_url),
                    bot_name,
                    bot.avatar_type,
                    conversation_id
                )
                upload(image, image_key)
                delete('uploads', image_url)

            logger.debug(f'[DEBUG] {bot.name}, {conversation_id}, {image_key}')
            avatar = Avatar.objects.create(
                bot=bot,
                bot_conversation=conversation_id,
                image_path=image_key
            )

            return JsonResponse(
                {"message": "SUCCESS!"},
                status=201
            )
        except Exception as e:
            logger.exception(f'[ERROR] {e}') 
            return JsonResponse(
                {'message': "FAILED!"},
                status=500
            )

@method_decorator(csrf_exempt, name='dispatch')
class AvatarDetailAPIView(View):
    def get(self, request, bot_name, *args, **kwargs):
        try:
            bot = Bot.objects.get(name=bot_name)
            data = {
                    "bot_id": bot.pk,
                    "bot_name": bot.name,
                    "avatar_type": bot.avatar_type,
                }
            
            if bot.avatar_type=="user":
                conversation_id = request.GET.get("conversation_id")
                avatar = Avatar.objects.get(bot=bot, bot_conversation=conversation_id)
            else:
                avatar = Avatar.objects.get(bot=bot, bot_conversation=None)

            if avatar.image_path:
                data['image_url'] = get_presigned_url('avatar', avatar.image_path)
            else:
                data['image_url'] = None
            return JsonResponse(data, status=200)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            logger.exception(f'[ERROR] {e}')

    def post(self, request, bot_name, *args, **kwargs):
        try:
            bot=Bot.objects.get(pk=int(bot_name))
            avatar = Avatar.objects.get(bot=bot, bot_conversation=None)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)

        try:
            image_key = None

            if avatar.image_path:
                delete('avatar', avatar.image_path)

            if bot.avatar_type == "default":
                data = json.loads(request.body)
                image_url = data.get("image_path")
                edit_image, image_key = generate_avatar(
                    download('uploads', image_url),
                    bot.name,
                    bot.avatar_type
                )
                upload(edit_image, image_key)
                delete('uploads', image_url)

            avatar.bot = bot
            avatar.image_path = image_key
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
                    delete('avatar', avatar.image_path)
            avatars.delete()
            return JsonResponse({"message": "Bot deleted successfully."}, status=204)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)