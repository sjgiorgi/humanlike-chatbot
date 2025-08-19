"""
Test script for the follow-up functionality
"""

import json
import time
from datetime import datetime

import pytest
from django.test import Client, TestCase

# Configuration
BOT_NAME = f"test_bot_followup_{int(time.time())}"
CONVERSATION_ID = f"test_followup_{int(time.time())}"
PARTICIPANT_ID = "test_participant"


@pytest.mark.django_db
class TestFollowupFunctionality(TestCase):
    def setUp(self):
        """Set up test data"""
        from chatbot.models import Bot, Model

        Model.get_or_create_default_models()
        self.model = Model.objects.first()

        self.bot = Bot.objects.create(
            name=BOT_NAME,
            prompt="You are a helpful assistant.",
            ai_model=self.model,
            follow_up_on_idle=True,
            idle_time_minutes=1,
            follow_up_instruction_prompt="Send a friendly follow-up message to keep the conversation going.",
        )

        self.client = Client()

    def test_followup_functionality(self):
        # Step 1: Initialize conversation
        init_data = {
            "bot_name": BOT_NAME,
            "conversation_id": CONVERSATION_ID,
            "participant_id": PARTICIPANT_ID,
            "study_name": "followup_test",
            "user_group": "test",
            "survey_id": "test_survey",
        }

        response = self.client.post(
            "/api/initialize_conversation/",
            data=json.dumps(init_data),
            content_type="application/json",
        )

        assert response.status_code == 200, (
            f"Failed to initialize conversation: {response.content}"
        )

        # Step 2: Send a user message
        chat_data = {
            "message": "Hello, how are you?",
            "bot_name": BOT_NAME,
            "conversation_id": CONVERSATION_ID,
            "participant_id": PARTICIPANT_ID,
        }

        response = self.client.post(
            "/api/chatbot/",
            data=json.dumps(chat_data),
            content_type="application/json",
        )

        assert response.status_code == 200, (
            f"Failed to send message: {response.content}"
        )

        # Step 3: Manually set the last user message to be idle (more than 1 minute ago)
        from datetime import timedelta

        from chatbot.models import Utterance

        # Get the last user message and set its created_time to be 2 minutes ago
        last_user_message = (
            Utterance.objects.filter(
                conversation__conversation_id=CONVERSATION_ID,
                speaker_id="user",
            )
            .order_by("-created_time")
            .first()
        )

        if last_user_message:
            last_user_message.created_time = datetime.now() - timedelta(minutes=2)
            last_user_message.save()

        # Step 4: Test follow-up endpoint
        followup_data = {
            "bot_name": BOT_NAME,
            "conversation_id": CONVERSATION_ID,
            "participant_id": PARTICIPANT_ID,
        }

        response = self.client.post(
            "/api/followup/",
            data=json.dumps(followup_data),
            content_type="application/json",
        )

        assert response.status_code == 200, (
            f"Follow-up request failed: {response.content}"
        )

        # Step 5: Test bot configuration endpoint
        response = self.client.get("/api/bots/")

        assert response.status_code == 200, (
            f"Failed to get bot configuration: {response.content}"
        )

        bots_response = response.json()

        # Handle different response formats
        if isinstance(bots_response, list):
            bot_names = [bot["name"] for bot in bots_response]
        elif isinstance(bots_response, dict) and "bots" in bots_response:
            bot_names = [bot["name"] for bot in bots_response["bots"]]
        else:
            # If it's a different format, just check that our bot name appears somewhere in the response
            response_str = str(bots_response)
            assert BOT_NAME in response_str, (
                f"Test bot {BOT_NAME} not found in response"
            )
            return True

        # Verify our test bot is in the list
        assert BOT_NAME in bot_names, f"Test bot {BOT_NAME} not found in bot list"

        return True
