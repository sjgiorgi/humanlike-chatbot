from unittest.mock import AsyncMock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache

from chatbot.models import Bot, Conversation, Utterance, Persona
from chatbot.services.runchat import run_chat_round
from chatbot.services.followup import run_followup_chat_round


class TestTranscriptLengthControl(TestCase):
    """Test cases for transcript length control functionality"""

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
        
        self.bot_limit_10 = Bot.objects.create(
            name="test_bot_limit_10",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=10  # Limit to 10 messages
        )
        
        # Create test conversation
        self.conversation = Conversation.objects.create(
            conversation_id="test_conversation_123",
            bot_name="test_bot_no_limit",
            participant_id="test_participant"
        )
        
        # Create test persona
        self.persona = Persona.objects.create(
            name="Test Persona",
            instructions="Be very helpful and friendly."
        )

    def tearDown(self):
        """Clean up after each test"""
        cache.clear()

    def create_mock_kani(self):
        """Helper method to create a properly mocked Kani instance"""
        mock_kani = AsyncMock()
        
        # Create a proper async iterator for full_round
        async def mock_full_round(*args, **kwargs):
            yield MagicMock(text="Test response")
        
        mock_kani.full_round = mock_full_round
        return mock_kani

    def create_test_utterances(self, count, conversation=None):
        """Helper method to create test utterances"""
        if conversation is None:
            conversation = self.conversation
            
        utterances = []
        for i in range(count):
            # Alternate between user and assistant messages
            speaker = "user" if i % 2 == 0 else "assistant"
            text = f"Message {i+1} from {speaker}"
            
            utterance = Utterance.objects.create(
                conversation=conversation,
                speaker_id=speaker,
                text=text,
                bot_name=self.bot_no_limit.name if speaker == "assistant" else None,
                participant_id="test_participant" if speaker == "user" else None
            )
            utterances.append(utterance)
        
        return utterances

    async def create_test_utterances_async(self, count, conversation=None):
        """Async helper method to create test utterances"""
        from asgiref.sync import sync_to_async
        
        if conversation is None:
            conversation = self.conversation
            
        utterances = []
        for i in range(count):
            # Alternate between user and assistant messages
            speaker = "user" if i % 2 == 0 else "assistant"
            text = f"Message {i+1} from {speaker}"
            
            utterance = await sync_to_async(Utterance.objects.create)(
                conversation=conversation,
                speaker_id=speaker,
                text=text,
                bot_name=self.bot_no_limit.name if speaker == "assistant" else None,
                participant_id="test_participant" if speaker == "user" else None
            )
            utterances.append(utterance)
        
        return utterances

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_no_transcript_limit(self, mock_save, mock_moderate, mock_engine):
        """Test that when max_transcript_length is 0, all messages are included"""
        # Create 15 messages in conversation
        await self.create_test_utterances_async(15)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round
            response = await run_chat_round(
                bot_name=self.bot_no_limit.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with all messages (15 original + 1 new = 16)
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have 16 messages (15 original + 1 new)
            assert len(chat_history) == 16
            assert "New user message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_5_messages(self, mock_save, mock_moderate, mock_engine):
        """Test that when max_transcript_length is 5, only 5 latest messages are included"""
        # Create 15 messages in conversation
        await self.create_test_utterances_async(15)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 5
            response = await run_chat_round(
                bot_name=self.bot_limit_5.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with only 5 messages (limit)
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have exactly 5 messages
            assert len(chat_history) == 5
            assert "New user message" in [msg.content for msg in chat_history]
            
            # Should contain the most recent messages
            message_contents = [msg.content for msg in chat_history]
            assert "Message 15 from assistant" in message_contents
            assert "Message 14 from user" in message_contents

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_less_than_existing(self, mock_save, mock_moderate, mock_engine):
        """Test when transcript limit is less than existing messages"""
        # Create only 3 messages in conversation
        await self.create_test_utterances_async(3)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 10 (more than existing)
            response = await run_chat_round(
                bot_name=self.bot_limit_10.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with all existing messages + new one
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have 4 messages (3 original + 1 new)
            assert len(chat_history) == 4
            assert "New user message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_exactly_matching(self, mock_save, mock_moderate, mock_engine):
        """Test when transcript limit exactly matches the number of messages"""
        # Create exactly 5 messages in conversation
        await self.create_test_utterances_async(5)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 5
            response = await run_chat_round(
                bot_name=self.bot_limit_5.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with exactly 5 messages (limit)
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have exactly 5 messages
            assert len(chat_history) == 5
            assert "New user message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_empty_conversation_with_limit(self, mock_save, mock_moderate, mock_engine):
        """Test with empty conversation and transcript limit"""
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with empty conversation
            response = await run_chat_round(
                bot_name=self.bot_limit_5.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="First message"
            )
            
            # Verify Kani was called with only the new message
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have only 1 message (the new one)
            assert len(chat_history) == 1
            assert "First message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.followup.get_or_create_engine')
    @patch('chatbot.services.moderation.moderate_message')
    @patch('chatbot.services.followup.save_chat_to_db')
    async def test_followup_with_transcript_limit(self, mock_save, mock_moderate, mock_engine):
        """Test that followup also respects transcript length limits"""
        # Create 15 messages in conversation
        await self.create_test_utterances_async(15)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.followup.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run followup chat round with bot that has limit of 5
            response = await run_followup_chat_round(
                bot_name=self.bot_limit_5.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                followup_instruction="Send a followup message"
            )
            
            # Verify Kani was called with only 5 messages (limit)
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have exactly 5 messages
            assert len(chat_history) == 5
            assert "Send a followup message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_with_persona(self, mock_save, mock_moderate, mock_engine):
        """Test transcript limit works correctly with persona selection"""
        # Set up conversation with persona
        from asgiref.sync import sync_to_async
        self.conversation.selected_persona = self.persona
        await sync_to_async(self.conversation.save)()
        
        # Create 15 messages in conversation
        await self.create_test_utterances_async(15)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 5
            response = await run_chat_round(
                bot_name=self.bot_limit_5.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with only 5 messages (limit)
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have exactly 5 messages
            assert len(chat_history) == 5
            assert "New user message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_edge_case_zero(self, mock_save, mock_moderate, mock_engine):
        """Test edge case where max_transcript_length is set to 0"""
        # Create 10 messages in conversation
        await self.create_test_utterances_async(10)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 0 (no limit)
            response = await run_chat_round(
                bot_name=self.bot_no_limit.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with all messages
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have all messages (10 original + 1 new = 11)
            assert len(chat_history) == 11
            assert "New user message" in [msg.content for msg in chat_history]

    @patch('chatbot.services.runchat.get_or_create_engine')
    @patch('chatbot.services.runchat.moderate_message')
    @patch('chatbot.services.runchat.save_chat_to_db')
    async def test_transcript_limit_edge_case_one(self, mock_save, mock_moderate, mock_engine):
        """Test edge case where max_transcript_length is set to 1"""
        # Create a bot with limit of 1
        from asgiref.sync import sync_to_async
        bot_limit_1 = await sync_to_async(Bot.objects.create)(
            name="test_bot_limit_1",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-4",
            max_transcript_length=1  # Limit to 1 message
        )
        
        # Create 5 messages in conversation
        await self.create_test_utterances_async(5)
        
        # Mock the engine and Kani
        mock_kani = self.create_mock_kani()
        mock_engine.return_value = MagicMock()
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            # Mock moderation to allow the message
            mock_moderate.return_value = None
            
            # Run chat round with bot that has limit of 1
            response = await run_chat_round(
                bot_name=bot_limit_1.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_participant",
                message="New user message"
            )
            
            # Verify Kani was called with only 1 message
            kani_call_args = mock_kani.__call__.call_args
            chat_history = kani_call_args[1]['chat_history']
            
            # Should have exactly 1 message (the new one)
            assert len(chat_history) == 1
            assert "New user message" in [msg.content for msg in chat_history]

    def test_bot_model_max_transcript_length_field(self):
        """Test that the max_transcript_length field is properly configured"""
        # Test default value
        bot = Bot.objects.create(
            name="test_bot_default",
            prompt="Test prompt",
            model_type="OpenAI",
            model_id="gpt-4"
        )
        assert bot.max_transcript_length == 0  # Default should be 0 (no limit)
        
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
