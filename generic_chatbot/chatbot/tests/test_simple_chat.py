import asyncio
from unittest.mock import patch, MagicMock
from django.test import TestCase
from asgiref.sync import sync_to_async

from chatbot.models import Bot, Conversation, Utterance
from chatbot.services.runchat import run_chat_round


class TestSimpleChat(TestCase):
    """Simple test using existing models to verify chat functionality"""

    def setUp(self):
        """Set up test using existing data"""
        # Get or create default models
        from chatbot.models import Model
        Model.get_or_create_default_models()
        self.model = Model.objects.first()
        
        if not self.model:
            self.skipTest("No models found in database.")
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Create a simple bot using existing model
        self.bot = Bot.objects.create(
            name=f"simple_test_bot_{timestamp}",
            prompt="You are a helpful assistant.",
            ai_model=self.model,
            max_transcript_length=1
        )
        
        # Create a conversation
        self.conversation = Conversation.objects.create(
            conversation_id=f"simple_test_conversation_{timestamp}",
            bot_name=self.bot.name,
            participant_id="test_user"
        )

    @patch('chatbot.services.moderation.moderate_message')
    @patch('server.engine.get_or_create_engine_from_model')
    async def test_simple_chat(self, mock_get_engine, mock_moderate):
        """Test simple chat functionality"""
        # Mock moderation to allow all messages
        mock_moderate.return_value = None
        
        # Mock engine
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        # Mock Kani responses
        mock_kani = MagicMock()
        
        async def mock_full_round(*args, **kwargs):
            yield MagicMock(text="Hello! I'm here to help.")
        
        mock_kani.full_round = mock_full_round
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            print(f"\n🧪 Testing Simple Chat with {self.model.display_name}")
            print("=" * 50)
            
            # Send a message
            response = await run_chat_round(
                bot_name=self.bot.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_user",
                message="Hello, how are you?"
            )
            
            # Verify response
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"✅ Bot responded: '{response[:50]}...'")
            
            # Verify database records
            utterances = await sync_to_async(list)(Utterance.objects.filter(
                conversation=self.conversation
            ).order_by('created_time'))
            
            self.assertEqual(len(utterances), 2)  # 1 user message + 1 bot response
            
            # Debug: Print all utterances
            print(f"📝 Found {len(utterances)} utterances:")
            for i, u in enumerate(utterances):
                print(f"  {i+1}. Speaker: '{u.speaker_id}', Text: '{u.text[:50]}...'")
            
            # Find user and bot messages (bot messages use 'assistant' as speaker_id)
            user_messages = [u for u in utterances if u.speaker_id == "user"]
            bot_messages = [u for u in utterances if u.speaker_id == "assistant"]
            
            print(f"👤 User messages: {len(user_messages)}")
            print(f"🤖 Bot messages: {len(bot_messages)}")
            
            self.assertEqual(len(user_messages), 1)
            self.assertEqual(len(bot_messages), 1)
            
            self.assertEqual(user_messages[0].text, "Hello, how are you?")
            self.assertGreater(len(bot_messages[0].text), 0)
            
            print("✅ Database records verified")
            print("✅ Simple chat test passed!")

    def test_model_info(self):
        """Test that we can access model information"""
        print(f"\n📊 Model Information:")
        print(f"Provider: {self.model.provider.display_name}")
        print(f"Model: {self.model.display_name}")
        print(f"Model ID: {self.model.model_id}")
        print(f"Capabilities: {', '.join(self.model.capabilities)}")
        
        # Verify model has required fields
        self.assertIsNotNone(self.model.provider)
        self.assertIsNotNone(self.model.model_id)
        self.assertIsNotNone(self.model.capabilities)
        print("✅ Model information verified")


def run_simple_test():
    """Run the simple chat test"""
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'generic_chatbot.settings')
    django.setup()
    
    # Create test instance and run tests
    test_instance = TestSimpleChat()
    test_instance.setUp()
    
    # Run the tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        print("\n🚀 Starting Simple Chat Test")
        print("=" * 40)
        
        # Test model info
        test_instance.test_model_info()
        
        # Test simple chat
        print("\nRunning simple chat test...")
        loop.run_until_complete(test_instance.test_simple_chat())
        
        print("\n✅ Simple chat test completed successfully!")
        
    finally:
        test_instance.tearDown()
        loop.close()


if __name__ == "__main__":
    run_simple_test()
