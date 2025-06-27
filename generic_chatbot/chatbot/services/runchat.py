from kani import ChatMessage, ChatRole, Kani
from asgiref.sync import sync_to_async
from django.core.cache import cache
from ..models import Bot, Conversation, Utterance
from server.engine import get_or_create_engine
import time
import random
import asyncio
from .moderation import moderate_message


async def save_chat_to_db(conversation_id, speaker_id, text, bot_name=None, participant_id=None):
    """
    Save chat messages asynchronously to the Utterance table.
    """
    try:
        conversation = await sync_to_async(Conversation.objects.get)(conversation_id=conversation_id)
        print(
            f"Found conversation {conversation.conversation_id}, inserting message...")

        await sync_to_async(Utterance.objects.create)(
            conversation=conversation,
            speaker_id=speaker_id,
            bot_name=bot_name,
            participant_id=participant_id,
            text=text
        )
        print("✅ Successfully saved message to Utterance table.")

    except Conversation.DoesNotExist:
        print(f"❌ Conversation with ID {conversation_id} not found.")
    except Exception as e:
        print(f"❌ Failed to save message to Utterance table: {e}")


async def run_chat_round(bot_name, conversation_id, participant_id, message):
    """
    Handles one full round of chat interaction: user -> bot response.
    Runs moderation on incoming message before processing.
    Returns the bot response text.
    """
    engine_instances = {}
    # Fetch bot object
    bot = await sync_to_async(Bot.objects.get)(name=bot_name)

    # Moderate incoming message
    # Run in thread to avoid blocking
    blocked = await sync_to_async(moderate_message)(message)
    if blocked:
        # Prepare a warning response without further processing
        warning_text = f"Your message was blocked by moderation due to: {blocked}"
        # Save both user message and moderation response
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="user",
            text=message,
            bot_name=None,
            participant_id=participant_id
        )
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="assistant",
            text=warning_text,
            bot_name=bot.name,
            participant_id=None
        )
        return warning_text

    # Retrieve history from cache
    cache_key = f"conversation_cache_{conversation_id}"
    conversation_history = cache.get(cache_key, [])

    # Append new message
    conversation_history.append({"role": "user", "content": message})

    # Format for Kani
    formatted_history = [
        ChatMessage(
            role=ChatRole.USER if msg["role"] == "user" else ChatRole.ASSISTANT,
            content=str(msg["content"])
        )
        for msg in conversation_history
    ]

    # Run Kani
    engine = get_or_create_engine(
        bot.model_type, bot.model_id, engine_instances)
    kani = Kani(engine, system_prompt=bot.prompt,
                chat_history=formatted_history)

    latest_user_message = formatted_history[-1].content
    response_text = ""

    # start timer
    start_time = time.time()

    async for msg in kani.full_round(query=latest_user_message):
        if hasattr(msg, "text") and isinstance(msg.text, str):
            response_text += msg.text + " "

    # end timer
    end_time = time.time()

    response_text = response_text.strip()

    # Append bot response
    conversation_history.append(
        {"role": "assistant", "content": response_text})
    cache.set(cache_key, conversation_history, timeout=3600)

    # Save to DB
    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="user",
        text=message,
        bot_name=None,
        participant_id=participant_id
    )

    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="assistant",
        text=response_text,
        bot_name=bot.name,
        participant_id=None
    )

    return response_text
