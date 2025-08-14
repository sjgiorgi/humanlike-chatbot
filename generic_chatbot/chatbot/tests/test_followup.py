#!/usr/bin/env python3
"""
Test script for the follow-up functionality
"""
import requests
import json
import time
from datetime import datetime
import pytest

# Configuration
API_BASE = "http://localhost:8000"
BOT_NAME = f"test_bot_followup_{int(time.time())}"
CONVERSATION_ID = f"test_followup_{int(time.time())}"
PARTICIPANT_ID = "test_participant"

@pytest.mark.django_db
def test_followup_functionality():
    print("🧪 Testing Follow-up Functionality")
    print("=" * 50)
    
    # Create test bot
    print("0. Creating test bot...")
    from chatbot.models import Bot, Model
    Model.get_or_create_default_models()
    model = Model.objects.first()
    
    bot = Bot.objects.create(
        name=BOT_NAME,
        prompt="You are a helpful assistant.",
        ai_model=model,
        follow_up_on_idle=True,
        idle_time_minutes=1
    )
    print(f"   Test bot created: {BOT_NAME}")
    print(f"   Idle time: {bot.idle_time_minutes} minutes")
    print(f"   Follow-up enabled: {bot.follow_up_on_idle}")
    
    # Step 1: Initialize conversation
    print("1. Initializing conversation...")
    init_data = {
        "bot_name": BOT_NAME,
        "conversation_id": CONVERSATION_ID,
        "participant_id": PARTICIPANT_ID,
        "study_name": "followup_test",
        "user_group": "test",
        "survey_id": "test_survey"
    }
    
    response = requests.post(f"{API_BASE}/api/initialize_conversation/", json=init_data)
    if response.status_code != 200:
        print(f"❌ Failed to initialize conversation: {response.text}")
        return False
    
    print("✅ Conversation initialized successfully")
    
    # Step 2: Send a user message
    print("\n2. Sending user message...")
    chat_data = {
        "message": "Hello, how are you?",
        "bot_name": BOT_NAME,
        "conversation_id": CONVERSATION_ID,
        "participant_id": PARTICIPANT_ID
    }
    
    response = requests.post(f"{API_BASE}/api/chatbot/", json=chat_data)
    if response.status_code != 200:
        print(f"❌ Failed to send message: {response.text}")
        return False
    
    print("✅ User message sent successfully")
    
    # Step 3: Wait a moment to simulate idle time
    print("\n3. Waiting 2 seconds to simulate idle time...")
    time.sleep(2)
    
    # Step 4: Test follow-up endpoint
    print("\n4. Testing follow-up endpoint...")
    followup_data = {
        "bot_name": BOT_NAME,
        "conversation_id": CONVERSATION_ID,
        "participant_id": PARTICIPANT_ID
    }
    
    response = requests.post(f"{API_BASE}/api/followup/", json=followup_data)
    if response.status_code != 200:
        print(f"❌ Follow-up request failed: {response.text}")
        return False
    
    followup_response = response.json()
    print("✅ Follow-up request successful!")
    print(f"   Response: {followup_response['response'][:100]}...")
    print(f"   Chunks: {len(followup_response['response_chunks'])}")
    print(f"   Is followup: {followup_response.get('is_followup', False)}")
    
    # Step 5: Test bot configuration endpoint
    print("\n5. Testing bot configuration endpoint...")
    response = requests.get(f"{API_BASE}/api/bots/")
    if response.status_code != 200:
        print(f"❌ Failed to get bot configuration: {response.text}")
        return False
    
    bots_data = response.json()
    bot = next((b for b in bots_data['bots'] if b['name'] == BOT_NAME), None)
    if bot:
        print("✅ Bot configuration retrieved successfully")
        print(f"   Follow-up enabled: {bot['follow_up_on_idle']}")
        print(f"   Idle time minutes: {bot['idle_time_minutes']}")
        print(f"   Follow-up prompt: {bot['follow_up_instruction_prompt'][:50]}...")
    else:
        print("❌ Bot not found in configuration")
        return False
    
    print("\n🎉 All tests passed! Follow-up functionality is working correctly.")
    
    # Restore original idle time
    bot.idle_time_minutes = original_idle_time
    bot.save()
    print(f"   Restored idle time to: {bot.idle_time_minutes} minutes")
    
    return True

if __name__ == "__main__":
    try:
        test_followup_functionality()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
