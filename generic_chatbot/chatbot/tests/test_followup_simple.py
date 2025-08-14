#!/usr/bin/env python3
"""
Simple test for followup functionality - one followup per idle period
"""
import os
import django
import time
from datetime import datetime, timedelta
import pytest

from chatbot.models import Bot, Conversation, Utterance
from chatbot.services.followup import generate_followup_message
import asyncio

@pytest.mark.django_db
def test_simple_followup():
    print("🧪 Testing Simple Followup - One per Idle Period")
    print("=" * 60)
    
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
        idle_time_minutes=1
    )
    
    print(f"✅ Bot configured: {BOT_NAME}")
    print(f"   Idle time: {bot.idle_time_minutes} minute")
    print(f"   Follow-up enabled: {bot.follow_up_on_idle}")
    
    # Create conversation
    conversation = Conversation.objects.create(
        conversation_id=CONVERSATION_ID,
        bot_name=BOT_NAME,
        participant_id=PARTICIPANT_ID,
        study_name="simple_test"
    )
    print(f"✅ Conversation created: {CONVERSATION_ID}")
    
    # Send initial user message with old timestamp (2 minutes ago)
    user_message = "Hello, this is a test"
    utterance = Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=user_message,
        participant_id=PARTICIPANT_ID
    )
    utterance.created_time = datetime.now() - timedelta(minutes=2)
    utterance.save()
    print(f"✅ User message saved: '{user_message}'")
    
    # Check initial utterance count
    initial_count = Utterance.objects.filter(conversation=conversation).count()
    print(f"📊 Initial utterance count: {initial_count}")
    
    # Test 1: Generate first followup
    print("\n🔄 Test 1: Generating first followup...")
    response1, error1 = asyncio.run(generate_followup_message(
        bot_name=BOT_NAME,
        conversation_id=CONVERSATION_ID,
        participant_id=PARTICIPANT_ID
    ))
    
    if error1:
        print(f"❌ First followup failed: {error1}")
        return False
    
    print(f"✅ First followup generated: '{response1[:50]}...'")
    
    # Check utterance count after first followup
    count_after_first = Utterance.objects.filter(conversation=conversation).count()
    print(f"📊 Utterance count after first followup: {count_after_first}")
    
    # Test 2: Try to generate second followup immediately (should be rate limited)
    print("\n🔄 Test 2: Trying second followup immediately...")
    response2, error2 = asyncio.run(generate_followup_message(
        bot_name=BOT_NAME,
        conversation_id=CONVERSATION_ID,
        participant_id=PARTICIPANT_ID
    ))
    
    if error2 and "recently sent" in error2:
        print(f"✅ Second followup properly rate limited: {error2}")
    else:
        print(f"❌ Second followup should have been rate limited")
        return False
    
    # Test 3: Send a new user message (should reset the rate limit)
    print("\n🔄 Test 3: Sending new user message...")
    new_user_message = "I'm back!"
    new_utterance = Utterance.objects.create(
        conversation=conversation,
        speaker_id="user",
        text=new_user_message,
        participant_id=PARTICIPANT_ID
    )
    print(f"✅ New user message saved: '{new_user_message}'")
    
    # Test 4: Try followup again after user message (should work)
    print("\n🔄 Test 4: Trying followup after user message...")
    response3, error3 = asyncio.run(generate_followup_message(
        bot_name=BOT_NAME,
        conversation_id=CONVERSATION_ID,
        participant_id=PARTICIPANT_ID
    ))
    
    if error3:
        print(f"❌ Third followup failed: {error3}")
        return False
    
    print(f"✅ Third followup generated: '{response3[:50]}...'")
    
    # Final check
    final_count = Utterance.objects.filter(conversation=conversation).count()
    print(f"\n📊 Final utterance count: {final_count}")
    
    # Verify no followup request messages in database
    followup_requests = Utterance.objects.filter(
        conversation=conversation,
        text__startswith="[FOLLOW-UP REQUEST]"
    )
    
    if followup_requests.exists():
        print(f"❌ ERROR: Found followup request messages in database!")
        return False
    else:
        print("✅ SUCCESS: No followup request messages in database")
    
    # Cleanup
    conversation.delete()
    bot.idle_time_minutes = original_idle_time
    bot.save()
    
    print("\n🎉 All tests passed! Followup works correctly:")
    print("   - One followup per idle period")
    print("   - Rate limiting prevents multiple followups")
    print("   - User interaction resets the rate limit")
    print("   - No followup requests saved to database")
    
    return True

if __name__ == "__main__":
    try:
        test_simple_followup()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
