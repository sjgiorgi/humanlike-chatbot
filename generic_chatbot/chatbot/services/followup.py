import json
import logging
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import Bot, Conversation, Utterance

# Dictionary to store engine instances for followup
followup_engine_instances = {}

logger = logging.getLogger(__name__)


async def get_last_user_message_time(conversation_id):
    """
    Get the timestamp of the last user message in a conversation.
    Returns None if no user messages exist.
    """
    try:
        last_user_utterance = await sync_to_async(Utterance.objects.filter)(
            conversation__conversation_id=conversation_id,
            speaker_id="user",
        )
        last_user_utterance = await sync_to_async(
            lambda: last_user_utterance.order_by("-created_time").first(),
        )()

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

    idle_threshold = datetime.now(last_message_time.tzinfo) - timedelta(
        minutes=idle_time_minutes,
    )
    return last_message_time < idle_threshold


async def run_followup_chat_round(
    bot_name,
    conversation_id,
    participant_id,
    followup_instruction,
):
    """
    Custom chat round for followup messages that doesn't save the followup request to database.
    Only saves the bot's response.
    """
    from kani import ChatMessage, ChatRole, Kani

    from server.engine import get_or_create_engine

    # Fetch bot object with personas prefetched
    bot = await sync_to_async(Bot.objects.prefetch_related("personas").get)(
        name=bot_name,
    )

    # Retrieve history from cache
    cache_key = f"conversation_cache_{conversation_id}"
    conversation_history = cache.get(cache_key, [])

    # If cache is empty, try to load from database
    if not conversation_history:
        try:
            conversation = await sync_to_async(Conversation.objects.get)(
                conversation_id=conversation_id,
            )
            utterances = await sync_to_async(list)(
                Utterance.objects.filter(conversation=conversation).order_by(
                    "created_time",
                ),
            )

            # Build conversation history from database
            for utterance in utterances:
                role = "user" if utterance.speaker_id == "user" else "assistant"
                conversation_history.append(
                    {"role": role, "content": utterance.text})

            # Populate cache
            cache.set(cache_key, conversation_history, timeout=3600)
            logger.info(
                f"Loaded {len(conversation_history)} messages from database for conversation {conversation_id}",
            )
        except Exception as e:
            logger.warning(
                f"Failed to load conversation history from database: {e}")
            conversation_history = []

    # Apply transcript length limit to history only (before adding followup instruction)
    if bot.max_transcript_length > 0:
        # Keep only the latest messages from history up to the limit
        conversation_history = conversation_history[-bot.max_transcript_length:]
        logger.info(
            f"Limited history to {len(conversation_history)} messages (max: {bot.max_transcript_length})",
        )
    elif bot.max_transcript_length == 0:
        # 0 means no chat history - clear history
        conversation_history = []
        logger.info("No chat history - using only current message")
    else:
        logger.info(
            f"No transcript limit applied, using all {len(conversation_history)} messages from history",
        )

    # Add followup instruction to history for AI processing (but don't save to DB)
    conversation_history.append(
        {"role": "user", "content": followup_instruction})

    # Format for Kani
    formatted_history = [
        ChatMessage(
            role=ChatRole.USER if msg["role"] == "user" else ChatRole.ASSISTANT,
            content=str(msg["content"]),
        )
        for msg in conversation_history
    ]

    # Get the selected persona for this conversation
    conversation = await sync_to_async(
        Conversation.objects.select_related("selected_persona").get,
    )(conversation_id=conversation_id)
    selected_persona = conversation.selected_persona

    # Generate dynamic system prompt combining bot prompt with selected persona
    from .runchat import generate_system_prompt

    system_prompt = generate_system_prompt(bot, selected_persona)

    # Run Kani
    engine = get_or_create_engine(
        bot.model_type,
        bot.model_id,
        followup_engine_instances,
    )
    kani = Kani(engine, system_prompt=system_prompt,
                chat_history=formatted_history)

    latest_user_message = formatted_history[-1].content
    response_text = ""

    async for msg in kani.full_round(query=latest_user_message):
        if hasattr(msg, "text") and isinstance(msg.text, str):
            response_text += msg.text + " "

    response_text = response_text.strip()

    # Capture the chat history that was actually used (before appending bot response)
    # Store only the chat history sent to LLM (excluding the new user message)
    chat_history_json = json.dumps(conversation_history[:-1], indent=2)

    # Update cache with the followup instruction and response (for future context)
    conversation_history.append(
        {"role": "assistant", "content": response_text})
    cache.set(cache_key, conversation_history, timeout=3600)

    # Only save the bot's response to database, NOT the followup request
    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="assistant",
        text=response_text,
        bot_name=bot.name,
        participant_id=None,
        instruction_prompt=system_prompt,
        chat_history_used=chat_history_json,
    )

    return response_text


async def save_chat_to_db(
    conversation_id,
    speaker_id,
    text,
    bot_name=None,
    participant_id=None,
    instruction_prompt=None,
    chat_history_used=None,
):
    """
    Save chat messages asynchronously to the Utterance table.
    """
    try:
        conversation = await sync_to_async(Conversation.objects.get)(
            conversation_id=conversation_id,
        )

        await sync_to_async(Utterance.objects.create)(
            conversation=conversation,
            speaker_id=speaker_id,
            bot_name=bot_name,
            participant_id=participant_id,
            text=text,
            instruction_prompt=instruction_prompt,
            chat_history_used=chat_history_used,
        )

    except Conversation.DoesNotExist:
        logger.warning(f"Conversation with ID {conversation_id} not found.")
    except Exception as e:
        logger.error(f"Failed to save message to Utterance table: {e}")
        import traceback

        traceback.print_exc()


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

        # Check if recurring followup is disabled and a followup was already sent in this idle period
        if not bot.recurring_followup:
            followup_sent_key = f"followup_sent_once_{conversation_id}"
            if cache.get(followup_sent_key):
                return (
                    None,
                    "Follow-up already sent for this idle period (recurring disabled)",
                )

        # Check if a followup was recently sent (within last 30 seconds) - only for rate limiting
        cache_key = f"followup_sent_{conversation_id}"
        if cache.get(cache_key):
            return None, "Follow-up was recently sent, please wait"

        # Set a flag to prevent multiple followups (30 second cooldown)
        cache.set(cache_key, True, timeout=30)

        # If recurring is disabled, set a flag that persists until user interaction
        if not bot.recurring_followup:
            followup_sent_key = f"followup_sent_once_{conversation_id}"
            cache.set(
                followup_sent_key,
                True,
                timeout=3600,
            )  # 1 hour timeout as fallback

        # Create a follow-up instruction using the instruction prompt
        followup_instruction = f"[FOLLOW-UP REQUEST] {bot.follow_up_instruction_prompt}"

        # Use the custom followup chat round function that doesn't save the request
        response_text = await run_followup_chat_round(
            bot_name=bot_name,
            conversation_id=conversation_id,
            participant_id=participant_id,
            followup_instruction=followup_instruction,
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
                    status=400,
                )

            # Check if this is a reset flag request
            reset_flag = data.get("reset_flag", False)
            if reset_flag:
                # Clear the "followup sent once" flag to allow followup again
                followup_sent_key = f"followup_sent_once_{conversation_id}"
                cache.delete(followup_sent_key)
                return JsonResponse({"status": "Followup flag reset"}, status=200)

            # Generate follow-up message
            response_text, error = await generate_followup_message(
                bot_name=bot_name,
                conversation_id=conversation_id,
                participant_id=participant_id,
            )

            if error:
                return JsonResponse({"error": error}, status=400)

            # Get bot configuration for chunking and delay
            try:
                bot = await sync_to_async(Bot.objects.get)(name=bot_name)
                use_chunks = bot.chunk_messages
                use_humanlike_delay = bot.humanlike_delay

                # Split response into chunks
                if use_chunks:
                    from .post_processing import (
                        calculate_typing_delays,
                        human_like_chunks,
                    )
                    response_chunks = human_like_chunks(response_text)
                else:
                    response_chunks = [response_text]

                # For followup messages, use empty message for reading delay calculation
                simulated_user_message = ""

                # Calculate delays using new system
                delay_data = calculate_typing_delays(
                    simulated_user_message, response_chunks, bot)

                delay_config = {
                    "reading_time": delay_data["reading_time"],
                    "min_reading_delay": delay_data["min_reading_delay"],
                    "response_segments": delay_data["response_segments"],
                }

            except Bot.DoesNotExist:
                use_chunks = True  # Default to chunking
                use_humanlike_delay = True  # Default to delay

                # Create default bot configuration for calculation
                class DefaultBotConfiguration:
                    humanlike_delay = True
                    reading_words_per_minute = 250.0
                    reading_jitter_min = 0.1
                    reading_jitter_max = 0.3
                    reading_thinking_min = 0.2
                    reading_thinking_max = 0.5
                    writing_words_per_minute = 200.0
                    writing_jitter_min = 0.05
                    writing_jitter_max = 0.15
                    writing_thinking_min = 0.1
                    writing_thinking_max = 0.3
                    intra_message_delay_min = 0.1
                    intra_message_delay_max = 0.3
                    min_reading_delay = 1.0

                default_bot = DefaultBotConfiguration()

                # Split response into chunks
                if use_chunks:
                    from .post_processing import (
                        calculate_typing_delays,
                        human_like_chunks,
                    )
                    response_chunks = human_like_chunks(response_text)
                else:
                    response_chunks = [response_text]

                # For followup messages, simulate a 10-word user message for reading delay calculation
                simulated_user_message = "How are you doing today? I hope you're having a great time!"

                # Calculate delays using new system
                delay_data = calculate_typing_delays(
                    simulated_user_message, response_chunks, default_bot)

                delay_config = {
                    "reading_time": delay_data["reading_time"],
                    "min_reading_delay": delay_data["min_reading_delay"],
                    "response_segments": delay_data["response_segments"],
                }

            return JsonResponse(
                {
                    "response": response_text,
                    "response_chunks": response_chunks,  # Keep for backward compatibility
                    "bot_name": bot_name,
                    "is_followup": True,
                    "humanlike_delay": use_humanlike_delay,
                    "chunk_messages": use_chunks,
                    "delay_config": delay_config,
                },
                status=200,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            logger.error(f"FollowupAPIView Exception: {e}")
            return JsonResponse({"error": str(e)}, status=500)
