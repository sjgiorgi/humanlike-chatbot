from asgiref.sync import sync_to_async
from django.core.cache import cache
from kani import ChatMessage, ChatRole, Kani

from server.engine import get_or_create_engine

from ..models import Bot, Conversation, Utterance
from .moderation import moderate_message


def generate_system_prompt(bot, selected_persona=None):
    """
    Generate a dynamic system prompt by combining the bot's base prompt 
    with instructions from the selected persona for this conversation.
    
    Args:
        bot: Bot instance with prompt
        selected_persona: Persona instance selected for this conversation (can be None)
        
    Returns:
        str: Combined system prompt
    """
    try:
        # Start with the bot's base prompt
        system_prompt = bot.prompt.strip() if bot.prompt else ""
        
        # Add selected persona instructions if available
        if selected_persona and hasattr(selected_persona, 'name') and hasattr(selected_persona, 'instructions'):
            # Combine base prompt with persona instructions
            if system_prompt:
                system_prompt += "\n\n"
            
            system_prompt += f"Additional personality instructions:\nPersona '{selected_persona.name}': {selected_persona.instructions}"
        
        return system_prompt
    except Exception as e:
        print(f"❌ Error generating system prompt: {e}")
        # Fallback to just the bot's prompt
        return bot.prompt.strip() if bot.prompt else ""


async def save_chat_to_db(
    conversation_id, speaker_id, text, bot_name=None, participant_id=None,
):
    """
    Save chat messages asynchronously to the Utterance table.
    """
    try:
        conversation = await sync_to_async(Conversation.objects.get)(
            conversation_id=conversation_id,
        )

        utterance = await sync_to_async(Utterance.objects.create)(
            conversation=conversation,
            speaker_id=speaker_id,
            bot_name=bot_name,
            participant_id=participant_id,
            text=text,
        )

    except Conversation.DoesNotExist:
        print(f"❌ Conversation with ID {conversation_id} not found.")
    except Exception as e:
        print(f"❌ Failed to save message to Utterance table: {e}")
        import traceback
        traceback.print_exc()


async def run_chat_round(bot_name, conversation_id, participant_id, message):
    """
    Handles one full round of chat interaction: user -> bot response.
    Runs moderation on incoming message before processing.
    Returns the bot response text.
    """
    engine_instances = {}
    # Fetch bot object with personas prefetched
    bot = await sync_to_async(Bot.objects.prefetch_related('personas').get)(name=bot_name)

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
            participant_id=participant_id,
        )
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="assistant",
            text=warning_text,
            bot_name=bot.name,
            participant_id=None,
        )
        return warning_text

    # Retrieve history from cache
    cache_key = f"conversation_cache_{conversation_id}"
    conversation_history = cache.get(cache_key, [])
    
    # If cache is empty, try to load from database
    if not conversation_history:
        try:
            conversation = await sync_to_async(Conversation.objects.get)(conversation_id=conversation_id)
            utterances = await sync_to_async(list)(Utterance.objects.filter(conversation=conversation).order_by("created_time"))
            
            # Build conversation history from database
            for utterance in utterances:
                role = "user" if utterance.speaker_id == "user" else "assistant"
                conversation_history.append({"role": role, "content": utterance.text})
            
            # Populate cache
            cache.set(cache_key, conversation_history, timeout=3600)
            print(f"📚 Loaded {len(conversation_history)} messages from database for conversation {conversation_id}")
        except Exception as e:
            print(f"⚠️ Failed to load conversation history from database: {e}")
            conversation_history = []

    # Append new message
    conversation_history.append({"role": "user", "content": message})

    # Format for Kani
    formatted_history = [
        ChatMessage(
            role=ChatRole.USER if msg["role"] == "user" else ChatRole.ASSISTANT,
            content=str(msg["content"]),
        )
        for msg in conversation_history
    ]

    # Get the selected persona for this conversation
    conversation = await sync_to_async(Conversation.objects.select_related('selected_persona').get)(conversation_id=conversation_id)
    selected_persona = conversation.selected_persona
    
    # Generate dynamic system prompt combining bot prompt with selected persona
    system_prompt = generate_system_prompt(bot, selected_persona)
    
    # Log the generated prompt for debugging
    print(f"🤖 Bot '{bot.name}' system prompt:")
    print(f"   Base prompt: {bot.prompt[:100] if bot.prompt else 'None'}...")
    print(f"   Selected persona: {selected_persona.name if selected_persona and hasattr(selected_persona, 'name') else 'None'}")
    print(f"   Final prompt length: {len(system_prompt)} characters")

    # Run Kani
    engine = get_or_create_engine(bot.model_type, bot.model_id, engine_instances)
    kani = Kani(engine, system_prompt=system_prompt, chat_history=formatted_history)

    latest_user_message = formatted_history[-1].content
    response_text = ""

    async for msg in kani.full_round(query=latest_user_message):
        if hasattr(msg, "text") and isinstance(msg.text, str):
            response_text += msg.text + " "

    response_text = response_text.strip()

    # Append bot response
    conversation_history.append({"role": "assistant", "content": response_text})
    cache.set(cache_key, conversation_history, timeout=3600)

    # Save to DB
    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="user",
        text=message,
        bot_name=None,
        participant_id=participant_id,
    )

    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="assistant",
        text=response_text,
        bot_name=bot.name,
        participant_id=None,
    )

    return response_text
