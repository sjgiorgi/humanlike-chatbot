#!/usr/bin/env python3
"""
Test script to verify that followup request messages are not saved to database
"""
import os
import django
import time
from datetime import datetime
import pytest

from chatbot.models import Bot, Conversation, Utterance
from chatbot.services.followup import generate_followup_message
import asyncio

@pytest.mark.django_db
def test_followup_not_saved_to_db():
    print("🧪 Testing Followup Request Not Saved to Database")
    print("=" * 60)
    
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
        idle_time_minutes=1
    )
    
    print(f"✅ Bot configured: {BOT_NAME}")
    print(f"   Idle time: {bot.idle_time_minutes} minutes")
    print(f"   Follow-up enabled: {bot.follow_up_on_idle}")
    
    # Create conversation
    conversation = Conversation.objects.create(
        conversation_id=CONVERSATION_ID,
        bot_name=BOT_NAME,
        participant_id=PARTICIPANT_ID,
        study_name="followup_db_test"
    )
    print(f"✅ Conversation created: {CONVERSATION_ID}")
    
    # Send a user message first
    user_message = "Hello, this is a test message"
    Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=user_message,
        participant_id=PARTICIPANT_ID
    )
    print(f"✅ User message saved: '{user_message[:30]}...'")
    
    # Check initial utterance count
    initial_count = Utterance.objects.filter(conversation=conversation).count()
    print(f"📊 Initial utterance count: {initial_count}")
    
    # Wait for idle time
    print("⏳ Waiting 2 seconds to trigger idle...")
    time.sleep(2)
    
    # Generate followup message
    print("🔄 Generating followup message...")
    response_text, error = asyncio.run(generate_followup_message(
        bot_name=BOT_NAME,
        conversation_id=CONVERSATION_ID,
        participant_id=PARTICIPANT_ID
    ))
    
    if error:
        print(f"❌ Followup generation failed: {error}")
        return False
    
    print(f"✅ Followup response generated: '{response_text[:50]}...'")
    
    # Check final utterance count
    final_count = Utterance.objects.filter(conversation=conversation).count()
    print(f"📊 Final utterance count: {final_count}")
    
    # Get all utterances to verify content
    utterances = Utterance.objects.filter(conversation=conversation).order_by('created_time')
    print("\n📝 All utterances in conversation:")
    for i, utterance in enumerate(utterances, 1):
        print(f"   {i}. [{utterance.speaker_id}] {utterance.text[:60]}...")
    
    # Verify no followup request message was saved
    followup_requests = Utterance.objects.filter(
        conversation=conversation,
        text__startswith="[FOLLOW-UP REQUEST]"
    )
    
    if followup_requests.exists():
        print(f"❌ ERROR: Found {followup_requests.count()} followup request messages in database!")
        for req in followup_requests:
            print(f"   - {req.text[:80]}...")
        return False
    else:
        print("✅ SUCCESS: No followup request messages found in database!")
    
    # Verify only the bot response was added
    expected_count = initial_count + 1  # Only the bot response should be added
    if final_count == expected_count:
        print(f"✅ SUCCESS: Correct utterance count ({final_count})")
    else:
        print(f"❌ ERROR: Expected {expected_count} utterances, got {final_count}")
        return False
    
    # Cleanup
    conversation.delete()
    bot.idle_time_minutes = original_idle_time
    bot.save()
    
    print("\n🎉 All tests passed! Followup request messages are correctly excluded from database.")
    return True

if __name__ == "__main__":
    try:
        test_followup_not_saved_to_db()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
