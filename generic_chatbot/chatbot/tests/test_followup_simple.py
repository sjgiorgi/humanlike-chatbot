"""
Simple test for followup functionality - one followup per idle period
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest

from chatbot.models import Bot, Conversation, Utterance
from chatbot.services.followup import generate_followup_message


@pytest.mark.django_db
def test_simple_followup():
    # Test configuration
    BOT_NAME = f"test_bot_simple_{int(time.time())}"
    CONVERSATION_ID = f"test_simple_{int(time.time())}"
    PARTICIPANT_ID = "test_user"

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
        study_name="simple_test",
    )

    # Send initial user message with old timestamp (2 minutes ago)
    user_message = "Hello, this is a test"
    utterance = Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=user_message,
        participant_id=PARTICIPANT_ID,
    )
    utterance.created_time = datetime.now() - timedelta(minutes=2)
    utterance.save()

    # Test 1: Generate first followup
    response1, error1 = asyncio.run(
        generate_followup_message(
            bot_name=BOT_NAME,
            conversation_id=CONVERSATION_ID,
            participant_id=PARTICIPANT_ID,
        ),
    )

    if error1:
        return False

    # Test 2: Try to generate second followup immediately (should be rate limited)
    response2, error2 = asyncio.run(
        generate_followup_message(
            bot_name=BOT_NAME,
            conversation_id=CONVERSATION_ID,
            participant_id=PARTICIPANT_ID,
        ),
    )

    if not error2 or "recently sent" not in error2:
        return False

    # Test 3: Send a new user message (should reset the rate limit)
    new_user_message = "I'm back!"
    Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=new_user_message,
        participant_id=PARTICIPANT_ID,
    )

    # Test 4: Try followup again after user message (should work)
    response3, error3 = asyncio.run(
        generate_followup_message(
            bot_name=BOT_NAME,
            conversation_id=CONVERSATION_ID,
            participant_id=PARTICIPANT_ID,
        ),
    )

    if error3:
        return False

    # Verify no followup request messages in database
    followup_requests = Utterance.objects.filter(
        conversation=conversation,
        text__startswith="[FOLLOW-UP REQUEST]",
    )

    if followup_requests.exists():
        return False

    # Cleanup
    conversation.delete()
    bot.delete()

    return True


if __name__ == "__main__":
    try:
        test_simple_followup()
    except Exception:
        import traceback

        traceback.print_exc()
