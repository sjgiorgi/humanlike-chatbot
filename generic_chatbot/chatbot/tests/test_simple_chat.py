"""
Simple test for basic chat functionality
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import django
import pytest
from asgiref.sync import sync_to_async

from chatbot.models import Bot, Conversation, Model, Utterance
from chatbot.services.runchat import run_chat_round

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "generic_chatbot.settings")
django.setup()


class TestSimpleChat:
    def setUp(self):
        """Set up test data"""
        # Create default models
        Model.get_or_create_default_models()
        self.model = Model.objects.first()

        # Create test bot
        self.bot = Bot.objects.create(
            name="test_bot",
            prompt="You are a helpful assistant.",
            ai_model=self.model,
        )

        # Create test conversation
        self.conversation = Conversation.objects.create(
            conversation_id="test_conversation",
            bot_name=self.bot.name,
            participant_id="test_user",
            study_name="test_study",
        )

    def tearDown(self):
        """Clean up test data"""
        self.conversation.delete()
        self.bot.delete()

    @pytest.mark.django_db
    @pytest.mark.asyncio
    async def test_simple_chat(self):
        """Test basic chat functionality"""
        # Set up test data
        await sync_to_async(self.setUp)()

        try:
            # Mock Kani response
            mock_kani = AsyncMock()

            # Create an async iterator for the full_round method
            async def mock_full_round(*args, **kwargs):
                yield MagicMock(
                    text="Hello! I'm doing well, thank you for asking. How can I help you today?",
                )

            mock_kani.full_round = mock_full_round

            # Mock Kani constructor
            with patch("chatbot.services.runchat.Kani", return_value=mock_kani):
                # Send a message
                response = await run_chat_round(
                    bot_name=self.bot.name,
                    conversation_id=self.conversation.conversation_id,
                    participant_id="test_user",
                    message="Hello, how are you?",
                )

                # Verify response
                assert isinstance(response, str)
                assert len(response) > 0

                # Verify database records
                utterances = await sync_to_async(list)(
                    Utterance.objects.filter(
                        conversation=self.conversation,
                    ).order_by("created_time"),
                )

                assert len(utterances) == 2  # 1 user message + 1 bot response

                # Find user and bot messages (bot messages use 'assistant' as speaker_id)
                user_messages = [u for u in utterances if u.speaker_id == "user"]
                bot_messages = [u for u in utterances if u.speaker_id == "assistant"]

                assert len(user_messages) == 1
                assert len(bot_messages) == 1

                assert user_messages[0].text == "Hello, how are you?"
                assert len(bot_messages[0].text) > 0
        finally:
            await sync_to_async(self.tearDown)()

    @pytest.mark.django_db
    def test_model_info(self):
        """Test that we can access model information"""
        # Set up test data
        self.setUp()

        try:
            # Verify model has required fields
            assert self.model.provider is not None
            assert self.model.model_id is not None
            assert self.model.capabilities is not None
        finally:
            self.tearDown()


def run_simple_test():
    """Run the simple chat test"""
    import os

    import django

    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "generic_chatbot.settings")
    django.setup()

    # Create test instance and run tests
    test_instance = TestSimpleChat()
    test_instance.setUp()

    # Run the tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Test model info
        test_instance.test_model_info()

        # Test simple chat
        loop.run_until_complete(test_instance.test_simple_chat())

    finally:
        test_instance.tearDown()
        loop.close()


if __name__ == "__main__":
    run_simple_test()
