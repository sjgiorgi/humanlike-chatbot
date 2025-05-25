import json
import sys
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from asgiref.sync import sync_to_async
from datetime import datetime
from django.core.cache import cache
from kani import Kani, ChatMessage, ChatRole
from .models import Conversation, Bot, Utterance
from .voicechat import get_realtime_session, upload_voice_utterance
from .bots import ListBotsAPIView, BotDetailAPIView
from .conversation import InitializeConversationAPIView
from .runchat import run_chat_round
from server.engine import get_or_create_engine

# Dictionary to store per-engine configurations
engine_instances = {}

def health_check(request):
    return JsonResponse({"status": "ok"})

@method_decorator(csrf_exempt, name='dispatch')
class ChatbotAPIView(View):
    async def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            bot_name = data.get('bot_name', '').strip()
            conversation_id = data.get('conversation_id')
            participant_id = data.get('participant_id')

            if not message or not bot_name or not conversation_id:
                return JsonResponse({"error": "Missing required fields."}, status=400)

            response_text = await run_chat_round(
                bot_name=bot_name,
                conversation_id=conversation_id,
                participant_id=participant_id,
                message=message
            )

            return JsonResponse({
                'message': message,
                'response': response_text,
                'bot_name': bot_name
            }, status=200)

        except Exception as e:
            print(f"❌ [ERROR] ChatbotAPIView Exception: {e}")
            return JsonResponse({'error': str(e)}, status=500)
