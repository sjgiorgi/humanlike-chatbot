import json
import logging
from datetime import datetime

from asgiref.sync import async_to_sync
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import Bot, Conversation, Utterance
from .runchat import save_chat_to_db

logger = logging.getLogger(__name__)


def load_conversation_history(conversation_id):
    """
    Load conversation history from database and populate cache.
    Returns the conversation history as a list of messages.
    """
    try:
        conversation = Conversation.objects.get(conversation_id=conversation_id)
        utterances = Utterance.objects.filter(conversation=conversation).order_by("created_time")
        
        # Build conversation history for cache
        conversation_history = []
        messages = []
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            content = utterance.text
            
            # Add to cache format
            conversation_history.append({"role": role, "content": content})
            
            # Add to frontend format
            messages.append({
                "sender": "You" if role == "user" else "AI Chatbot",
                "content": content,
            })
        
        # Populate cache
        cache_key = f"conversation_cache_{conversation_id}"
        cache.set(cache_key, conversation_history, timeout=3600)
        
        logger.debug(f"Loaded {len(messages)} messages for conversation {conversation_id}")
        return conversation, messages
        
    except Conversation.DoesNotExist:
        logger.debug(f"Conversation {conversation_id} not found")
        return None, []
    except Exception as e:
        logger.exception(f"Error loading conversation history: {e}")
        return None, []


@method_decorator(csrf_exempt, name="dispatch")
class InitializeConversationAPIView(View):
    def post(self, request, *args, **kwargs):
        try:
            logger.debug("Entering InitializeConversationAPIView.post()")

            try:
                data = json.loads(request.body)
            except Exception as parse_error:
                logger.debug("JSON parse error: %s", parse_error)
                return JsonResponse(
                    {"error": "Invalid JSON in request body."}, status=400,
                )

            logger.debug("Received JSON data: %r", data)

            conversation_id = data.get("conversation_id")
            bot_name = data.get("bot_name")
            participant_id = data.get("participant_id")
            study_name = data.get("study_name", "n/a")
            user_group = data.get("user_group", "n/a")
            survey_id = data.get("survey_id", "n/a")
            survey_meta_data = json.dumps(data)

            if not bot_name or not conversation_id:
                return JsonResponse(
                    {"error": "Both 'bot_name' and 'conversation_id' are required."},
                    status=400,
                )

            try:
                bot = Bot.objects.get(name=bot_name)
                logger.debug("Found bot: %s", bot_name)
            except Bot.DoesNotExist:
                return JsonResponse(
                    {"error": f"No bot found with the name '{bot_name}'."}, status=404,
                )
            except Exception:
                logger.exception("Error fetching bot")
                return JsonResponse(
                    {"error": "Error fetching the bot from the database."}, status=500,
                )

            # Check if conversation already exists
            existing_conversation, existing_messages = load_conversation_history(conversation_id)
            
            if existing_conversation:
                logger.debug(f"Conversation {conversation_id} already exists, returning existing data")
                return JsonResponse(
                    {
                        "conversation_id": conversation_id,
                        "message": "Conversation loaded successfully.",
                        "initial_utterance": existing_conversation.initial_utterance or "",
                        "existing_messages": existing_messages,
                        "is_existing": True,
                    },
                    status=200,
                )

            # Create new conversation
            try:
                Conversation.objects.create(
                    conversation_id=conversation_id,
                    bot_name=bot.name,
                    participant_id=participant_id,
                    initial_utterance=bot.initial_utterance,
                    study_name=study_name,
                    user_group=user_group,
                    survey_id=survey_id,
                    survey_meta_data=survey_meta_data,
                    started_time=datetime.now(),
                )
                logger.debug("Conversation created.")
            except Exception:
                logger.exception("Error creating Conversation")
                return JsonResponse(
                    {"error": "Failed to create Conversation."}, status=500,
                )

            # ✅ Save bot's initial utterance as an assistant message
            initial_messages = []
            if bot.initial_utterance and bot.initial_utterance.strip():
                try:
                    async_to_sync(save_chat_to_db)(
                        conversation_id=conversation_id,
                        speaker_id="assistant",
                        text=bot.initial_utterance.strip(),
                        bot_name=bot.name,
                        participant_id=None,
                    )
                    logger.debug("Initial bot message saved to DB.")
                    
                    # Add to initial messages for frontend
                    initial_messages.append({
                        "sender": "AI Chatbot",
                        "content": bot.initial_utterance.strip(),
                    })
                except Exception as e:
                    logger.exception("Failed to save initial bot message: %s", str(e))

            return JsonResponse(
                {
                    "conversation_id": conversation_id,
                    "message": "Conversation initialized successfully.",
                    "initial_utterance": bot.initial_utterance or "",
                    "existing_messages": initial_messages,
                    "is_existing": False,
                },
                status=200,
            )

        except Exception:
            logger.exception("Unhandled exception in InitializeConversationAPIView")
            return JsonResponse({"error": "Unexpected error occurred."}, status=500)
