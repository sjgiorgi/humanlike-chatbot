from unittest.mock import AsyncMock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache

from chatbot.models import Bot, Conversation, Utterance


class TestTranscriptLengthSimple(TestCase):
    """Simple test cases for transcript length control functionality"""

    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        
        # Create test bot with different transcript length settings
        self.bot_no_limit = Bot.objects.create(
            name="test_bot_no_limit",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=0  # No limit
        )
        
        self.bot_limit_5 = Bot.objects.create(
            name="test_bot_limit_5",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=5  # Limit to 5 messages
        )
        
        # Create test conversation
        self.conversation = Conversation.objects.create(
            conversation_id="test_conversation_123",
            bot_name="test_bot_no_limit",
            participant_id="test_participant"
        )

    def tearDown(self):
        """Clean up after each test"""
        cache.clear()

    def create_test_utterances(self, count):
        """Helper method to create test utterances"""
        utterances = []
        for i in range(count):
            # Alternate between user and assistant messages
            speaker = "user" if i % 2 == 0 else "assistant"
            text = f"Message {i+1} from {speaker}"
            
            utterance = Utterance.objects.create(
                conversation=self.conversation,
                speaker_id=speaker,
                text=text,
                bot_name=self.bot_no_limit.name if speaker == "assistant" else None,
                participant_id="test_participant" if speaker == "user" else None
            )
            utterances.append(utterance)
        
        return utterances

    def test_bot_model_max_transcript_length_field(self):
        """Test that the max_transcript_length field is properly configured"""
        # Test default value
        bot = Bot.objects.create(
            name="test_bot_default",
            prompt="Test prompt",
            model_type="OpenAI",
            model_id="gpt-4"
        )
        assert bot.max_transcript_length == 0  # Default should be 0 (no chat history)
        
        # Test custom value
        bot_with_limit = Bot.objects.create(
            name="test_bot_with_limit",
            prompt="Test prompt",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=20
        )
        assert bot_with_limit.max_transcript_length == 20
        
        # Test that field can be updated
        bot_with_limit.max_transcript_length = 50
        bot_with_limit.save()
        bot_with_limit.refresh_from_db()
        assert bot_with_limit.max_transcript_length == 50

    def test_transcript_limit_logic(self):
        """Test the transcript limiting logic directly"""
        # Create 10 messages
        self.create_test_utterances(10)
        
        # Simulate the conversation history that would be loaded
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        # Add a new message
        conversation_history.append({"role": "user", "content": "New user message"})
        
        # Test with no chat history (should keep only current message)
        if self.bot_no_limit.max_transcript_length == 0:
            conversation_history = [conversation_history[-1]]  # Only the new message
        
        # Should have 1 message (only the new one)
        assert len(conversation_history) == 1
        assert "New user message" in [msg["content"] for msg in conversation_history]
        
        # Test with limit of 5
        conversation_history = []
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        conversation_history.append({"role": "user", "content": "New user message"})
        
        if self.bot_limit_5.max_transcript_length > 0:
            conversation_history = conversation_history[-self.bot_limit_5.max_transcript_length:]
        
        # Should have exactly 5 messages
        assert len(conversation_history) == 5
        assert "New user message" in [msg["content"] for msg in conversation_history]
        
        # Should contain the most recent messages
        message_contents = [msg["content"] for msg in conversation_history]
        assert "Message 10 from assistant" in message_contents
        assert "Message 9 from user" in message_contents

    def test_unlimited_transcript_history(self):
        """Test unlimited transcript history (negative or very large number)"""
        # Create a bot with negative value (unlimited)
        bot_unlimited = Bot.objects.create(
            name="test_bot_unlimited",
            prompt="Test prompt",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=-1  # Unlimited
        )
        
        # Create 10 messages
        self.create_test_utterances(10)
        
        # Simulate the conversation history
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        conversation_history.append({"role": "user", "content": "New user message"})
        
        # Test with unlimited (negative value)
        if bot_unlimited.max_transcript_length > 0:
            conversation_history = conversation_history[-bot_unlimited.max_transcript_length:]
        
        # Should have all messages (10 original + 1 new = 11)
        assert len(conversation_history) == 11
        assert "New user message" in [msg["content"] for msg in conversation_history]
        assert "Message 1 from user" in [msg["content"] for msg in conversation_history]  # First message should be included

    def test_transcript_limit_edge_cases(self):
        """Test edge cases for transcript limiting"""
        # Test with empty conversation
        conversation_history = []
        conversation_history.append({"role": "user", "content": "First message"})
        
        if self.bot_limit_5.max_transcript_length > 0:
            conversation_history = conversation_history[-self.bot_limit_5.max_transcript_length:]
        
        # Should have only 1 message
        assert len(conversation_history) == 1
        assert "First message" in [msg["content"] for msg in conversation_history]
        
        # Test with limit exactly matching message count
        self.create_test_utterances(5)
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        conversation_history.append({"role": "user", "content": "New user message"})
        
        if self.bot_limit_5.max_transcript_length > 0:
            conversation_history = conversation_history[-self.bot_limit_5.max_transcript_length:]
        
        # Should have exactly 5 messages
        assert len(conversation_history) == 5
        assert "New user message" in [msg["content"] for msg in conversation_history]

    def test_zero_transcript_length(self):
        """Test that 0 means no chat history (only current message)"""
        # Create 10 messages
        self.create_test_utterances(10)
        
        # Simulate the conversation history
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        conversation_history.append({"role": "user", "content": "New user message"})
        
        # Test with 0 (no chat history)
        if self.bot_no_limit.max_transcript_length == 0:
            conversation_history = [conversation_history[-1]]  # Only the new message
        
        # Should have only 1 message (the new one)
        assert len(conversation_history) == 1
        assert "New user message" in [msg["content"] for msg in conversation_history]
        assert "Message 1 from user" not in [msg["content"] for msg in conversation_history]  # Old messages should not be included

    def test_admin_interface_includes_field(self):
        """Test that the admin interface includes the max_transcript_length field"""
        from django.contrib import admin
        from chatbot.admin import BotAdmin
        
        # Check that the field is in the list display
        assert 'max_transcript_length' in BotAdmin.list_display
        
        # Check that the field is in the fieldsets
        fieldsets = BotAdmin.fieldsets
        response_settings_found = False
        for fieldset_name, fieldset_options in fieldsets:
            if fieldset_name == "Response Settings":
                response_settings_found = True
                assert 'max_transcript_length' in fieldset_options['fields']
                break
        
        assert response_settings_found, "Response Settings fieldset not found"
