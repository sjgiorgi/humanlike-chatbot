import json
from datetime import datetime
from django.views import View
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.core.files.base import ContentFile
from asgiref.sync import async_to_sync
from ..models import Conversation, Bot, Avatar
from .runchat import save_chat_to_db 
import mimetypes
import os
import io
import openai
import requests
from PIL import Image
import base64

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
    image_vector = Image.open(file)
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
    image.name = f"{bot_name}_{avatar_type}_{conversation_id if conversation_id else ''}_{str(int(datetime.now().timestamp()))}_avatar.png"
    return image

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
            bot_name = request.POST.get("bot_name")
            bot = Bot.objects.get(name=bot_name)
            conversation_id = request.POST.get("conversation_id")
            image = None

            if bot.avatar_type == "default":
                image = generate_avatar(
                    request.FILES.get("image"),
                    bot_name,
                    bot.avatar_type
                )
            if bot.avatar_type == "user" and conversation_id:
                image = generate_avatar(
                    request.FILES.get("image"),
                    bot_name,
                    bot.avatar_type,
                    conversation_id
                )
            avatar = Avatar.objects.create(
                bot=bot,
                bot_conversation=conversation_id,
                image=image
            )

            return JsonResponse(
                {"message": "SUCCESS!"},
                status=201
            )
        except Exception as e:
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

            if avatar.image:
                with open(avatar.image.path, "rb") as f:
                    encoded_string = base64.b64encode(f.read()).decode()
                    data["image_base64"] = f"data:image/png;base64,{encoded_string}"
            else:
                data["image_base64"] = None
            return JsonResponse(data, status=200)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)

    def post(self, request, bot_name, *args, **kwargs):
        try:
            bot=Bot.objects.get(pk=int(bot_name))
            avatar = Avatar.objects.get(bot=bot, bot_conversation=None)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)

        try:
            edit_image = None

            if avatar.image:
                avatar.image.delete(save=False)

            if bot.avatar_type == "default":
                edit_image = generate_avatar(
                    request.FILES.get("image"),
                    bot.name,
                    bot.avatar_type
                )

            avatar.bot = bot
            avatar.image = edit_image
            avatar.save()

            return JsonResponse({"message": "Avatar updated successfully."}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, bot_name, *args, **kwargs):
        try:
            # bot = Bot.objects.get(name=bot_name)
            avatars = Avatar.objects.filter(bot=Bot.objects.filter(name=bot_name))
            for avatar in avatars:
                if avatar.image and os.path.isfile(avatar.image):
                    os.remove(avatar.image)
            avatars.delete()
            return JsonResponse({"message": "Bot deleted successfully."}, status=204)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)