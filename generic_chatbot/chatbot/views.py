import json
import logging

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Bot
from .services.post_processing import human_like_chunks
from .services.runchat import run_chat_round

# Get logger for this module
logger = logging.getLogger(__name__)

# Dictionary to store per-engine configurations
engine_instances = {}


def health_check(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
def test_upload(request):
    """Simple test endpoint to check if file uploads work"""
    if request.method == "POST":
        if request.FILES:
            file_info = []
            for field_name, uploaded_file in request.FILES.items():
                file_info.append(
                    {
                        "field_name": field_name,
                        "file_name": uploaded_file.name,
                        "file_size": uploaded_file.size,
                        "content_type": uploaded_file.content_type,
                    },
                )
            return JsonResponse(
                {
                    "status": "success",
                    "message": "File upload test successful",
                    "files": file_info,
                },
            )
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "No files received",
                },
                status=400,
            )
    else:
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method allowed",
            },
            status=405,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ChatbotAPIView(View):
    async def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            message = data.get("message", "").strip()
            bot_name = data.get("bot_name", "").strip()
            conversation_id = data.get("conversation_id")
            participant_id = data.get("participant_id")

            if not message or not bot_name or not conversation_id:
                return JsonResponse({"error": "Missing required fields."}, status=400)

            response_text = await run_chat_round(
                bot_name=bot_name,
                conversation_id=conversation_id,
                participant_id=participant_id,
                message=message,
            )

            # Get bot-specific settings
            try:
                bot = await sync_to_async(Bot.objects.get)(name=bot_name)
                use_chunks = bot.chunk_messages
                use_humanlike_delay = bot.humanlike_delay
                delay_config = {
                    "typing_speed_min_ms": bot.typing_speed_min_ms,
                    "typing_speed_max_ms": bot.typing_speed_max_ms,
                    "question_thinking_ms": bot.question_thinking_ms,
                    "first_chunk_thinking_ms": bot.first_chunk_thinking_ms,
                    "last_chunk_pause_ms": bot.last_chunk_pause_ms,
                    "min_delay_ms": bot.min_delay_ms,
                    "max_delay_ms": bot.max_delay_ms,
                }
            except Bot.DoesNotExist:
                # Use defaults if bot not found
                use_chunks = True
                use_humanlike_delay = True
                delay_config = {
                    "typing_speed_min_ms": 100,
                    "typing_speed_max_ms": 200,
                    "question_thinking_ms": 300,
                    "first_chunk_thinking_ms": 600,
                    "last_chunk_pause_ms": 100,
                    "min_delay_ms": 200,
                    "max_delay_ms": 800,
                }

            # split or not
            if use_chunks:
                response_chunks = human_like_chunks(response_text)
            else:
                response_chunks = [response_text]

            return JsonResponse(
                {
                    "message": message,
                    "response": response_text,
                    "response_chunks": response_chunks,
                    "bot_name": bot_name,
                    "humanlike_delay": use_humanlike_delay,
                    "delay_config": delay_config,
                },
                status=200,
            )

        except Exception as e:
            logger.error(f"❌ [ERROR] ChatbotAPIView Exception: {e}")
            return JsonResponse({"error": str(e)}, status=500)
