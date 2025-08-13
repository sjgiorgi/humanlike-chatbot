from unittest.mock import AsyncMock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache
import json

from chatbot.models import Bot, Conversation, Utterance


class TestChatHistoryCapture(TestCase):
    """Test cases for chat history capture functionality"""

    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        
        # Create test bot
        self.bot = Bot.objects.create(
            name="test_bot",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=5  # Limit to 5 messages
        )
        
        # Create test conversation
        self.conversation = Conversation.objects.create(
            conversation_id="test_conversation_123",
            bot_name="test_bot",
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
                bot_name=self.bot.name if speaker == "assistant" else None,
                participant_id="test_participant" if speaker == "user" else None
            )
            utterances.append(utterance)
        
        return utterances

    def test_chat_history_field_exists(self):
        """Test that the chat_history_used field exists in the model"""
        # Create a test utterance
        utterance = Utterance.objects.create(
            conversation=self.conversation,
            speaker_id="user",
            text="Test message",
            participant_id="test_participant"
        )
        
        # Check that the field exists and can be set
        test_history = json.dumps([{"role": "user", "content": "Test message"}])
        utterance.chat_history_used = test_history
        utterance.save()
        
        # Refresh from database
        utterance.refresh_from_db()
        
        # Verify the field was saved
        self.assertEqual(utterance.chat_history_used, test_history)

    def test_chat_history_json_format(self):
        """Test that chat history is stored in proper JSON format"""
        # Create a test utterance with chat history
        test_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        utterance = Utterance.objects.create(
            conversation=self.conversation,
            speaker_id="assistant",
            text="I'm doing well, thanks!",
            bot_name=self.bot.name,
            chat_history_used=json.dumps(test_history, indent=2)
        )
        
        # Verify the JSON can be parsed back
        parsed_history = json.loads(utterance.chat_history_used)
        self.assertEqual(len(parsed_history), 3)
        self.assertEqual(parsed_history[0]["role"], "user")
        self.assertEqual(parsed_history[0]["content"], "Hello")
        self.assertEqual(parsed_history[1]["role"], "assistant")
        self.assertEqual(parsed_history[1]["content"], "Hi there!")

    def test_chat_history_with_transcript_limit(self):
        """Test that chat history reflects the transcript limit"""
        # Create 10 messages in conversation
        self.create_test_utterances(10)
        
        # Simulate the conversation history that would be loaded
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        # Add a new message
        conversation_history.append({"role": "user", "content": "New user message"})
        
        # Apply transcript limit (should keep only 5 messages)
        if self.bot.max_transcript_length > 0:
            conversation_history = conversation_history[-self.bot.max_transcript_length:]
        
        # Create a test utterance with the limited history (excluding new user message)
        chat_history_used = conversation_history[:-1]  # Exclude the new user message
        test_utterance = Utterance.objects.create(
            conversation=self.conversation,
            speaker_id="assistant",
            text="Test response",
            bot_name=self.bot.name,
            chat_history_used=json.dumps(chat_history_used, indent=2)
        )
        
        # Verify the history was limited correctly
        parsed_history = json.loads(test_utterance.chat_history_used)
        self.assertEqual(len(parsed_history), 4)  # Should be limited to 4 messages (excluding new user message)
        
        # Should contain the most recent messages from history
        message_contents = [msg["content"] for msg in parsed_history]
        self.assertIn("Message 10 from assistant", message_contents)
        self.assertIn("Message 9 from user", message_contents)
        self.assertNotIn("New user message", message_contents)  # New user message should not be in chat history

    def test_chat_history_with_zero_limit(self):
        """Test that chat history with zero limit only contains current message"""
        # Create a bot with zero limit
        bot_zero = Bot.objects.create(
            name="test_bot_zero",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=0  # No chat history
        )
        
        # Create 5 messages in conversation
        self.create_test_utterances(5)
        
        # Simulate the conversation history
        conversation_history = []
        utterances = Utterance.objects.filter(conversation=self.conversation).order_by("created_time")
        
        for utterance in utterances:
            role = "user" if utterance.speaker_id == "user" else "assistant"
            conversation_history.append({"role": role, "content": utterance.text})
        
        # Add a new message
        conversation_history.append({"role": "user", "content": "New user message"})
        
        # Apply zero limit (should keep only current message)
        if bot_zero.max_transcript_length == 0:
            conversation_history = [conversation_history[-1]]  # Only the new message
        
        # Create a test utterance with the limited history (excluding new user message)
        chat_history_used = conversation_history[:-1]  # Exclude the new user message
        test_utterance = Utterance.objects.create(
            conversation=self.conversation,
            speaker_id="assistant",
            text="Test response",
            bot_name=bot_zero.name,
            chat_history_used=json.dumps(chat_history_used, indent=2)
        )
        
        # Verify the history was limited correctly
        parsed_history = json.loads(test_utterance.chat_history_used)
        self.assertEqual(len(parsed_history), 0)  # Should be 0 messages (no chat history)
        # No messages should be in chat history since new user message is passed separately

    def test_admin_interface_includes_chat_history_field(self):
        """Test that the admin interface includes the chat_history_used field"""
        from django.contrib import admin
        from chatbot.admin import UtteranceAdmin
        
        # Check that the field is in the list display
        assert 'chat_history_used_preview' in UtteranceAdmin.list_display
        
        # Check that the field is in the fieldsets
        fieldsets = UtteranceAdmin.fieldsets
        message_content_found = False
        for fieldset_name, fieldset_options in fieldsets:
            if fieldset_name == "Message Content":
                message_content_found = True
                assert 'chat_history_used' in fieldset_options['fields']
                break
        
        assert message_content_found, "Message Content fieldset not found"

    def test_chat_history_preview_method(self):
        """Test the admin preview method for chat history"""
        from chatbot.admin import UtteranceAdmin
        
        # Create test utterance with chat history
        test_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        utterance = Utterance.objects.create(
            conversation=self.conversation,
            speaker_id="assistant",
            text="Test response",
            bot_name=self.bot.name,
            chat_history_used=json.dumps(test_history, indent=2)
        )
        
        # Test the preview method
        admin_instance = UtteranceAdmin(Utterance, None)
        preview = admin_instance.chat_history_used_preview(utterance)
        
        # Should show "2 messages"
        self.assertIn("2 messages", preview)
        
        # Test with no chat history
        utterance.chat_history_used = None
        utterance.save()
        preview = admin_instance.chat_history_used_preview(utterance)
        self.assertIn("No chat history", preview)
