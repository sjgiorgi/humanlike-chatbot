import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import Avatar, Bot
from .s3_helper import delete

# Get logger for this module
logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ListBotsAPIView(View):
    """
    GET  -> List all bots
    POST -> Create a new bot
    """

    def get(self, request, *args, **kwargs):
        try:
            bots = Bot.objects.values(
                "id",
                "name",
                "model_type",
                "model_id",
                "prompt",
                "initial_utterance",
                "avatar_type",
                "chunk_messages",
                "follow_up_on_idle",
                "idle_time_minutes",
                "follow_up_instruction_prompt",
            )
            return JsonResponse({"bots": list(bots)}, status=200)
        except Exception as e:
            logger.error(f"Error in ListBotsAPIView GET: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get("name")
            model_type = data.get("model_type")
            model_id = data.get("model_id")
            prompt = data.get("prompt", "")
            initial_utterance = data.get("initial_utterance", "")
            avatar_type = data.get("avatar_type", "none")

            if not name or not model_type or not model_id:
                return JsonResponse({"error": "Missing required fields."}, status=400)

            bot = Bot.objects.create(
                name=name,
                model_type=model_type,
                model_id=model_id,
                prompt=prompt,
                initial_utterance=initial_utterance,
                avatar_type=avatar_type,
            )

            return JsonResponse(
                {
                    "id": bot.id,
                    "name": bot.name,
                    "model_type": bot.model_type,
                    "model_id": bot.model_id,
                    "prompt": bot.prompt,
                    "initial_utterance": bot.initial_utterance,
                    "avatar_type": bot.avatar_type,
                },
                status=201,
            )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            logger.error(f"Error in ListBotsAPIView POST: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class BotDetailAPIView(View):
    """
    GET    -> Retrieve single bot by ID
    PUT    -> Update an existing bot by ID
    DELETE -> Delete a bot by ID
    """

    def get(self, request, pk, *args, **kwargs):
        try:
            bot = Bot.objects.get(pk=pk)
            data = {
                "id": bot.id,
                "name": bot.name,
                "model_type": bot.model_type,
                "model_id": bot.model_id,
                "prompt": bot.prompt,
                "initial_utterance": bot.initial_utterance,
                "avatar_type": bot.avatar_type,
                "chunk_messages": bot.chunk_messages,
                "follow_up_on_idle": bot.follow_up_on_idle,
                "idle_time_minutes": bot.idle_time_minutes,
                "follow_up_instruction_prompt": bot.follow_up_instruction_prompt,
            }
            return JsonResponse(data, status=200)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            logger.error(f"Error in BotDetailAPIView GET: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def put(self, request, pk, *args, **kwargs):
        try:
            bot = Bot.objects.get(pk=pk)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)

        try:
            data = json.loads(request.body)
            bot.name = data.get("name", bot.name)
            bot.model_type = data.get("model_type", bot.model_type)
            bot.model_id = data.get("model_id", bot.model_id)
            bot.prompt = data.get("prompt", bot.prompt)
            bot.initial_utterance = data.get("initial_utterance", bot.initial_utterance)
            bot.avatar_type = data.get("avatar_type", bot.avatar_type)
            bot.save()

            return JsonResponse({"message": "Bot updated successfully."}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            logger.error(f"Error in BotDetailAPIView PUT: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def delete(self, request, pk, *args, **kwargs):
        try:
            bot = Bot.objects.get(pk=pk)
            try:
                avatars = Avatar.objects.filter(bot=bot)
                for avatar in avatars:
                    if avatar.image_path:
                        delete("avatar", avatar.image_path)
                avatars.delete()
            except Exception:
                logger.error("[ERROR] failed to delete S3 images")
            bot.delete()
            return JsonResponse({"message": "Bot deleted successfully."}, status=204)
        except Bot.DoesNotExist:
            return JsonResponse({"error": "Bot not found"}, status=404)
        except Exception as e:
            logger.error(f"Error in BotDetailAPIView DELETE: {e}")
            return JsonResponse({"error": str(e)}, status=500)
