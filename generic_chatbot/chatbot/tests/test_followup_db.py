"""
Test script to verify that followup request messages are not saved to database
"""

import asyncio
import time

import pytest

from chatbot.models import Bot, Conversation, Utterance
from chatbot.services.followup import generate_followup_message


@pytest.mark.django_db
def test_followup_not_saved_to_db():
    # Test configuration
    BOT_NAME = f"test_bot_db_{int(time.time())}"
    CONVERSATION_ID = f"test_followup_db_{int(time.time())}"
    PARTICIPANT_ID = "test_participant_db"

    # Create test bot
    from chatbot.models import Model

    Model.get_or_create_default_models()
    model = Model.objects.first()

    bot = Bot.objects.create(
        name=BOT_NAME,
        prompt="You are a helpful assistant.",
        ai_model=model,
        follow_up_on_idle=True,
        idle_time_minutes=1,
    )

    # Create conversation
    conversation = Conversation.objects.create(
        conversation_id=CONVERSATION_ID,
        bot_name=BOT_NAME,
        participant_id=PARTICIPANT_ID,
        study_name="followup_db_test",
    )

    # Send a user message first
    user_message = "Hello, this is a test message"
    Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=user_message,
        participant_id=PARTICIPANT_ID,
    )

    # Check initial utterance count
    initial_count = Utterance.objects.filter(conversation=conversation).count()

    # Wait for idle time
    time.sleep(2)

    # Generate followup message
    _response_text, error = asyncio.run(
        generate_followup_message(
            bot_name=BOT_NAME,
            conversation_id=CONVERSATION_ID,
            participant_id=PARTICIPANT_ID,
        ),
    )

    if error:
        return False

    # Check final utterance count
    final_count = Utterance.objects.filter(conversation=conversation).count()

    # Verify no followup request message was saved
    followup_requests = Utterance.objects.filter(
        conversation=conversation,
        text__startswith="[FOLLOW-UP REQUEST]",
    )

    if followup_requests.exists():
        return False

    # Verify only the bot response was added
    expected_count = initial_count + 1  # Only the bot response should be added
    if final_count != expected_count:
        return False

    # Cleanup
    conversation.delete()
    bot.delete()

    return True


if __name__ == "__main__":
    try:
        test_followup_not_saved_to_db()
    except Exception:
        import traceback

        traceback.print_exc()
