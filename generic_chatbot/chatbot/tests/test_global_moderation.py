from unittest.mock import MagicMock, patch

from django.test import TestCase

from ..models import Bot, Model, ModelProvider, ModerationSettings
from ..services.moderation import is_moderation_enabled, moderate_message


class TestGlobalModeration(TestCase):
    """Test global moderation enable/disable functionality."""

    def setUp(self):
        """Set up test data."""
        # Create default models
        Model.get_or_create_default_models()
        self.provider = ModelProvider.objects.get(name="OpenAI")
        self.model = Model.objects.filter(provider=self.provider).first()

        # Create a test bot
        self.bot = Bot.objects.create(
            name="test_moderation_bot",
            prompt="Test bot for moderation",
            ai_model=self.model,
        )

    def tearDown(self):
        """Clean up test data."""
        # Clean up moderation settings
        ModerationSettings.objects.all().delete()

    @patch("chatbot.services.moderation.OpenAI")
    def test_moderation_disabled_bypasses_api_call(self, mock_openai):
        """Test that when global moderation is disabled, OpenAI API is not called."""
        # Setup: Disable global moderation
        ModerationSettings.objects.create(enabled=False)

        # Create mock OpenAI instance
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        # Test message that would normally be blocked
        test_message = "This is a test message"

        # Call moderate_message
        result = moderate_message(test_message, self.bot)

        # Assertions
        assert result == ""  # Should return empty string (allow)
        mock_openai_instance.moderations.create.assert_not_called()  # API should not be called

    @patch("chatbot.services.moderation.OpenAI")
    def test_moderation_enabled_calls_api(self, mock_openai):
        """Test that when global moderation is enabled, OpenAI API is called."""
        # Setup: Enable global moderation
        ModerationSettings.objects.create(enabled=True)

        # Create mock OpenAI instance and response
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        # Mock the moderation response (no violations)
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.category_scores = None
        mock_response.results = [mock_result]
        mock_openai_instance.moderations.create.return_value = mock_response

        # Mock model_dump to return empty dict (no violations)
        with patch("chatbot.services.moderation.model_dump") as mock_model_dump:
            mock_model_dump.return_value = {}

            # Test message
            test_message = "This is a test message"

            # Call moderate_message
            result = moderate_message(test_message, self.bot)

            # Assertions
            assert result == ""  # Should return empty string (allow)
            mock_openai_instance.moderations.create.assert_called_once()  # API should be called

    def test_is_moderation_enabled_helper_function(self):
        """Test the is_moderation_enabled helper function."""
        # Test when no settings exist (should default to True)
        assert is_moderation_enabled()

        # Test when enabled
        ModerationSettings.objects.create(enabled=True)
        assert is_moderation_enabled()

        # Test when disabled
        ModerationSettings.objects.all().delete()
        ModerationSettings.objects.create(enabled=False)
        assert not is_moderation_enabled()

    @patch("chatbot.services.moderation.OpenAI")
    def test_moderation_enabled_with_violation_blocks_message(self, mock_openai):
        """Test that when moderation is enabled and violation detected, message is blocked."""
        # Setup: Enable global moderation
        ModerationSettings.objects.create(enabled=True)

        # Create mock OpenAI instance and response
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance

        # Mock the moderation response (harassment violation)
        mock_response = MagicMock()
        mock_result = MagicMock()
        mock_result.category_scores = None
        mock_response.results = [mock_result]
        mock_openai_instance.moderations.create.return_value = mock_response

        # Mock model_dump to return our test data
        with patch("chatbot.services.moderation.model_dump") as mock_model_dump:
            mock_model_dump.return_value = {
                "harassment": 0.8}  # Above threshold

            # Test message
            test_message = "This message has harassment content"

            # Call moderate_message
            result = moderate_message(test_message, self.bot)

            # Assertions
            assert result == "harassment"  # Should return violation category
            mock_openai_instance.moderations.create.assert_called_once()  # API should be called
