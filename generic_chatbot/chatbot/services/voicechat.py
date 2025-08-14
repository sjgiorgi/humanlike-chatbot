import logging
import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..models import Conversation, Utterance

# Get logger for this module
logger = logging.getLogger(__name__)


@csrf_exempt
@require_GET
def get_realtime_session(request):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "voice": "alloy",  # change voice if needed
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers=headers,
            json=data,
        )
        return JsonResponse(response.json(), status=response.status_code)
    except Exception as e:
        logger.error(f"Error fetching realtime session: {e}")
        return JsonResponse({"error": "Failed to get session from OpenAI"}, status=500)


@csrf_exempt
@require_POST
def upload_voice_utterance(request):
    try:
        audio_file = request.FILES.get("audio")
        transcript = request.POST.get("transcript", "")
        conversation_id = request.POST.get("conversation_id")
        participant_id = request.POST.get("participant_id")
        bot_name = request.POST.get("bot_name")
        is_voice = request.POST.get("is_voice", "").lower() == "true"

        logger.info(
            "📥 Received:",
            {
                "transcript": transcript,
                "bot_name": bot_name,
                "participant_id": participant_id,
                "is_voice": is_voice,
            },
        )

        # Validate required IDs
        if not conversation_id:
            return JsonResponse({"error": "Missing conversation_id."}, status=400)

        if not transcript and not audio_file:
            return JsonResponse(
                {"error": "Must include either transcript or audio."},
                status=400,
            )

        conversation = Conversation.objects.get(conversation_id=conversation_id)

        if bot_name:
            speaker_id = "assistant"
        else:
            speaker_id = "participant"

        utterance = Utterance.objects.create(
            conversation=conversation,
            speaker_id=speaker_id,
            bot_name=bot_name if speaker_id == "assistant" else None,
            participant_id=participant_id if speaker_id == "participant" else None,
            text=transcript,
            audio_file=audio_file,
            is_voice=is_voice,
        )
        return JsonResponse({"message": "Saved successfully", "id": utterance.id})

    except Conversation.DoesNotExist:
        logger.error(f"Conversation ID '{conversation_id}' not found.")
        return JsonResponse({"error": "Conversation not found."}, status=404)
    except Exception as e:
        logger.error(f"Failed to save voice/text utterance: {e}")
        return JsonResponse({"error": "Failed to save utterance"}, status=500)
