import logging
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from ..models import Bot, Conversation, Utterance
from .runchat import run_chat_round

logger = logging.getLogger(__name__)


async def get_last_user_message_time(conversation_id):
    """
    Get the timestamp of the last user message in a conversation.
    Returns None if no user messages exist.
    """
    try:
        last_user_utterance = await sync_to_async(Utterance.objects.filter)(
            conversation__conversation_id=conversation_id,
            speaker_id="user"
        )
        last_user_utterance = await sync_to_async(lambda: last_user_utterance.order_by('-created_time').first())()
        
        return last_user_utterance.created_time if last_user_utterance else None
    except Exception as e:
        logger.error(f"Error getting last user message time: {e}")
        return None


async def is_user_idle(conversation_id, idle_time_minutes):
    """
    Check if user is idle based on last message timestamp.
    Returns True if user is idle, False otherwise.
    """
    last_message_time = await get_last_user_message_time(conversation_id)
    if not last_message_time:
        return False
    
    idle_threshold = datetime.now(last_message_time.tzinfo) - timedelta(minutes=idle_time_minutes)
    return last_message_time < idle_threshold


async def generate_followup_message(bot_name, conversation_id, participant_id):
    """
    Generate a follow-up message when user is idle.
    Uses the bot's follow-up instruction prompt to guide the response.
    """
    try:
        # Get bot configuration
        bot = await sync_to_async(Bot.objects.get)(name=bot_name)
        
        if not bot.follow_up_on_idle:
            return None, "Follow-up not enabled for this bot"
        
        if not bot.follow_up_instruction_prompt:
            return None, "No follow-up instruction prompt configured"
        
        # Check if user is actually idle
        is_idle = await is_user_idle(conversation_id, bot.idle_time_minutes)
        if not is_idle:
            return None, "User is not idle"
        
        # Create a follow-up message using the instruction prompt
        followup_message = f"[FOLLOW-UP REQUEST] {bot.follow_up_instruction_prompt}"
        
        # Use the existing chat round function to generate response
        response_text = await run_chat_round(
            bot_name=bot_name,
            conversation_id=conversation_id,
            participant_id=participant_id,
            message=followup_message,
        )
        
        return response_text, None
        
    except Bot.DoesNotExist:
        return None, f"Bot '{bot_name}' not found"
    except Exception as e:
        logger.error(f"Error generating follow-up message: {e}")
        return None, str(e)


@method_decorator(csrf_exempt, name="dispatch")
class FollowupAPIView(View):
    """
    API endpoint for generating follow-up messages when user is idle.
    """
    
    async def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            bot_name = data.get("bot_name", "").strip()
            conversation_id = data.get("conversation_id")
            participant_id = data.get("participant_id")

            if not bot_name or not conversation_id:
                return JsonResponse(
                    {"error": "Missing required fields: bot_name and conversation_id"}, 
                    status=400
                )

            # Generate follow-up message
            response_text, error = await generate_followup_message(
                bot_name=bot_name,
                conversation_id=conversation_id,
                participant_id=participant_id,
            )

            if error:
                return JsonResponse({"error": error}, status=400)

            # Get bot configuration for chunking
            try:
                bot = await sync_to_async(Bot.objects.get)(name=bot_name)
                use_chunks = bot.chunk_messages
            except Bot.DoesNotExist:
                use_chunks = True  # Default to chunking

            # Apply chunking if enabled
            if use_chunks:
                from .post_processing import human_like_chunks
                response_chunks = human_like_chunks(response_text)
            else:
                response_chunks = [response_text]

            return JsonResponse(
                {
                    "response": response_text,
                    "response_chunks": response_chunks,
                    "bot_name": bot_name,
                    "is_followup": True,
                },
                status=200,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            logger.error(f"FollowupAPIView Exception: {e}")
            return JsonResponse({"error": str(e)}, status=500)
