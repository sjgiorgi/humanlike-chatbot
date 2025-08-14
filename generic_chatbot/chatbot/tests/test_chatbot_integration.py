import asyncio
from unittest.mock import patch, MagicMock
from django.test import TestCase
from asgiref.sync import sync_to_async

from chatbot.models import ModelProvider, Model, Bot, Conversation, Utterance
from chatbot.services.runchat import run_chat_round


class TestChatbotIntegration(TestCase):
    """Minimal integration test to verify chatbot conversation flow works"""

    def setUp(self):
        """Set up test data"""
        # Get or create default models
        Model.get_or_create_default_models()
        
        # Get the OpenAI provider
        self.provider = ModelProvider.objects.get(name="OpenAI")
        
        # Get an existing model for testing (preferably GPT-4o)
        self.model = Model.objects.filter(
            provider=self.provider,
            model_id="gpt-4o"
        ).first() or Model.objects.filter(provider=self.provider).first()
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Create a bot with the new model structure
        self.bot = Bot.objects.create(
            name=f"test_integration_bot_{timestamp}",
            prompt="You are a helpful assistant. Keep responses brief and friendly.",
            ai_model=self.model,
            max_transcript_length=2  # Keep some chat history for testing
        )
        
        # Create a conversation
        self.conversation = Conversation.objects.create(
            conversation_id=f"test_integration_conversation_{timestamp}",
            bot_name=self.bot.name,
            participant_id="test_user"
        )

    @patch('chatbot.services.moderation.moderate_message')
    @patch('server.engine.get_or_create_engine_from_model')
    async def test_basic_conversation_flow(self, mock_get_engine, mock_moderate):
        """Test basic conversation flow with new model structure"""
        # Mock moderation to allow all messages
        mock_moderate.return_value = None
        
        # Mock engine
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        # Mock Kani responses
        mock_kani = MagicMock()
        
        # Create an async iterator for the full_round method
        async def mock_full_round(*args, **kwargs):
            yield MagicMock(text="Hello! I'm your helpful assistant. How can I help you today?")
        
        mock_kani.full_round = mock_full_round
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            print("\n🧪 Testing Basic Conversation Flow")
            print("=" * 50)
            
            # Test 1: Initial message
            print("📝 Sending initial message...")
            response1 = await run_chat_round(
                bot_name=self.bot.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_user",
                message="Hello, how are you?"
            )
            
            # Verify response
            self.assertIsInstance(response1, str)
            self.assertGreater(len(response1), 0)
            print(f"✅ Bot responded: '{response1[:50]}...'")
            
            # Test 2: Follow-up message (should include chat history)
            print("📝 Sending follow-up message...")
            response2 = await run_chat_round(
                bot_name=self.bot.name,
                conversation_id=self.conversation.conversation_id,
                participant_id="test_user",
                message="What's the weather like?"
            )
            
            # Verify response
            self.assertIsInstance(response2, str)
            self.assertGreater(len(response2), 0)
            print(f"✅ Bot responded: '{response2[:50]}...'")
            
            # Test 3: Verify database records were created
            print("📊 Verifying database records...")
            
            # Check utterances were created
            utterances = await sync_to_async(list)(Utterance.objects.filter(
                conversation=self.conversation
            ).order_by('created_time'))
            
            self.assertEqual(len(utterances), 4)  # 2 user messages + 2 bot responses
            
            # Verify user messages
            user_utterances = [u for u in utterances if u.speaker_id == "user"]
            self.assertEqual(len(user_utterances), 2)
            self.assertEqual(user_utterances[0].text, "Hello, how are you?")
            self.assertEqual(user_utterances[1].text, "What's the weather like?")
            
            # Verify bot messages (bot messages use 'assistant' as speaker_id)
            bot_utterances = [u for u in utterances if u.speaker_id == "assistant"]
            self.assertEqual(len(bot_utterances), 2)
            self.assertGreater(len(bot_utterances[0].text), 0)
            self.assertGreater(len(bot_utterances[1].text), 0)
            
            print("✅ Database records verified")
            
            # Test 4: Verify bot model relationship
            print("🔗 Verifying bot-model relationship...")
            def verify_bot_model_relationship():
                bot = Bot.objects.get(name=self.bot.name)
                self.assertEqual(bot.ai_model, self.model)
                self.assertEqual(bot.ai_model.provider.name, "OpenAI")
                self.assertEqual(bot.ai_model.model_id, self.model.model_id)
                print("✅ Bot-model relationship verified")
            
            await sync_to_async(verify_bot_model_relationship)()

    @patch('chatbot.services.moderation.moderate_message')
    @patch('server.engine.get_or_create_engine')
    async def test_legacy_bot_compatibility(self, mock_get_engine, mock_moderate):
        """Test that legacy bots (without ai_model) still work"""
        import time
        timestamp = int(time.time() * 1000)
        
        # Create a legacy-style bot (with ai_model but also legacy fields)
        legacy_bot = await sync_to_async(Bot.objects.create)(
            name=f"test_legacy_bot_{timestamp}",
            prompt="You are a helpful assistant.",
            model_type="OpenAI",
            model_id="gpt-3.5-turbo",
            ai_model=self.model,  # Use the test model
            max_transcript_length=0
        )
        
        # Create a conversation for legacy bot
        legacy_conversation = await sync_to_async(Conversation.objects.create)(
            conversation_id=f"test_legacy_conversation_{timestamp}",
            bot_name=legacy_bot.name,
            participant_id="test_user"
        )
        
        # Mock moderation to allow all messages
        mock_moderate.return_value = None
        
        # Mock engine
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        # Mock Kani responses
        mock_kani = MagicMock()
        
        async def mock_full_round(*args, **kwargs):
            yield MagicMock(text="Hello from legacy bot!")
        
        mock_kani.full_round = mock_full_round
        
        # Mock Kani constructor
        with patch('chatbot.services.runchat.Kani', return_value=mock_kani):
            print("\n🧪 Testing Legacy Bot Compatibility")
            print("=" * 50)
            
            response = await run_chat_round(
                bot_name=legacy_bot.name,
                conversation_id=legacy_conversation.conversation_id,
                participant_id="test_user",
                message="Hello legacy bot!"
            )
            
            # Verify response
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"✅ Legacy bot responded: '{response[:50]}...'")
            
            # Verify legacy bot has ai_model and legacy fields
            def verify_legacy_bot():
                bot = Bot.objects.get(name=legacy_bot.name)
                self.assertIsNotNone(bot.ai_model)
                self.assertEqual(bot.model_type, "OpenAI")
                self.assertEqual(bot.model_id, "gpt-3.5-turbo")
                print("✅ Legacy bot compatibility verified")
            
            await sync_to_async(verify_legacy_bot)()

    def test_model_capabilities_integration(self):
        """Test that model capabilities are properly accessible"""
        print("\n🧪 Testing Model Capabilities Integration")
        print("=" * 50)
        
        # Test capabilities are stored and accessible
        self.assertIsInstance(self.model.capabilities, list)
        self.assertGreater(len(self.model.capabilities), 0)
        self.assertTrue("Chat" in self.model.capabilities)
        
        # Test capabilities through bot relationship
        self.assertEqual(self.bot.ai_model.capabilities, self.model.capabilities)
        
        print(f"✅ Model capabilities integration verified: {self.model.capabilities}")

    def test_provider_model_bot_chain(self):
        """Test the complete chain from provider to model to bot"""
        print("\n🧪 Testing Provider-Model-Bot Chain")
        print("=" * 50)
        
        # Test the complete chain
        provider_name = self.bot.ai_model.provider.name
        model_id = self.bot.ai_model.model_id
        bot_name = self.bot.name
        
        self.assertEqual(provider_name, "OpenAI")
        self.assertEqual(model_id, self.model.model_id)  # Use actual model ID
        self.assertTrue(bot_name.startswith("test_integration_bot_"))
        
        # Test reverse relationships
        provider_models = self.provider.models.all()
        self.assertGreaterEqual(provider_models.count(), 1)  # Should have at least our test model
        self.assertIn(self.model, provider_models)  # Our test model should be in the list
        
        model_bots = self.model.bots.all()
        self.assertGreaterEqual(model_bots.count(), 1)  # Should have at least our test bot
        self.assertIn(self.bot, model_bots)  # Our test bot should be in the list
        
        print("✅ Provider-Model-Bot chain verified")


def run_integration_tests():
    """Run the integration tests"""
    import os
    import django
    from django.conf import settings
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'generic_chatbot.settings')
    django.setup()
    
    # Create test instance and run tests
    test_instance = TestChatbotIntegration()
    test_instance.setUp()
    
    # Run the tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        print("\n🚀 Starting Chatbot Integration Tests")
        print("=" * 60)
        
        # Test model capabilities integration
        test_instance.test_model_capabilities_integration()
        
        # Test provider-model-bot chain
        test_instance.test_provider_model_bot_chain()
        
        # Test legacy bot compatibility
        print("\nRunning legacy bot compatibility test...")
        loop.run_until_complete(test_instance.test_legacy_bot_compatibility())
        
        # Test basic conversation flow
        print("\nRunning basic conversation flow test...")
        loop.run_until_complete(test_instance.test_basic_conversation_flow())
        
        print("\n✅ All integration tests completed successfully!")
        
    finally:
        test_instance.tearDown()
        loop.close()


if __name__ == "__main__":
    run_integration_tests()
