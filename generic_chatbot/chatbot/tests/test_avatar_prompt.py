from unittest.mock import MagicMock, patch

from django.test import TestCase
from PIL import Image

from chatbot.models import Bot, Model, ModelProvider
from chatbot.services.avatar import generate_avatar


class TestAvatarPrompt(TestCase):
    def setUp(self):
        # Create a test provider and model
        self.provider, _ = ModelProvider.objects.get_or_create(
            name="OpenAI",
            defaults={
                "display_name": "OpenAI",
                "description": "Test provider",
            },
        )
        self.model, _ = Model.objects.get_or_create(
            provider=self.provider,
            model_id="gpt-4o-mini",
            defaults={
                "display_name": "GPT-4o Mini",
                "capabilities": ["Chat"],
            },
        )

        # Create a test bot with custom avatar prompt
        self.bot_with_prompt = Bot.objects.create(
            name="TestBotWithPrompt",
            prompt="Test prompt",
            ai_model=self.model,
            avatar_type="default",
            avatar_prompt="Create a custom avatar with specific features",
        )

        # Create a test bot without avatar prompt
        self.bot_without_prompt = Bot.objects.create(
            name="TestBotWithoutPrompt",
            prompt="Test prompt",
            ai_model=self.model,
            avatar_type="default",
            avatar_prompt="",
        )

    def test_bot_has_avatar_prompt_field(self):
        """Test that the avatar_prompt field exists and works"""
        assert (
            self.bot_with_prompt.avatar_prompt
            == "Create a custom avatar with specific features"
        )
        assert self.bot_without_prompt.avatar_prompt == ""

    @patch("chatbot.services.avatar.openai.OpenAI")
    @patch("os.getenv")
    def test_generate_avatar_uses_bot_prompt(self, mock_getenv, mock_openai):
        """Test that generate_avatar uses the bot's avatar_prompt when available"""
        # Mock environment variable
        mock_getenv.return_value = "Default environment prompt"

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].url = "http://example.com/test.png"
        mock_client.images.edit.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock requests.get for downloading image
        with patch("chatbot.services.avatar.requests.get") as mock_requests:
            mock_response_requests = MagicMock()
            mock_response_requests.content = b"fake_image_data"
            mock_requests.return_value = mock_response_requests

            # Create a test image
            test_image = Image.new("RGB", (100, 100), color="red")

            # Test with bot that has custom prompt
            generate_avatar(
                test_image,
                self.bot_with_prompt,
                "default",
            )

            # Verify the custom prompt was used
            mock_client.images.edit.assert_called_once()
            call_args = mock_client.images.edit.call_args
            assert (
                call_args[1]["prompt"]
                == "Create a custom avatar with specific features"
            )

    @patch("chatbot.services.avatar.openai.OpenAI")
    @patch("os.getenv")
    def test_generate_avatar_falls_back_to_env_prompt(self, mock_getenv, mock_openai):
        """Test that generate_avatar falls back to environment variable when bot has no prompt"""
        # Mock environment variable
        mock_getenv.return_value = "Default environment prompt"

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].url = "http://example.com/test.png"
        mock_client.images.edit.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock requests.get for downloading image
        with patch("chatbot.services.avatar.requests.get") as mock_requests:
            mock_response_requests = MagicMock()
            mock_response_requests.content = b"fake_image_data"
            mock_requests.return_value = mock_response_requests

            # Create a test image
            test_image = Image.new("RGB", (100, 100), color="red")

            # Test with bot that has no prompt
            generate_avatar(
                test_image,
                self.bot_without_prompt,
                "default",
            )

            # Verify the environment prompt was used
            mock_client.images.edit.assert_called_once()
            call_args = mock_client.images.edit.call_args
            assert call_args[1]["prompt"] == "Default environment prompt"

    def test_default_avatar_prompt_populated(self):
        """Test that existing bots have the default avatar prompt populated"""
        # Check that the data migration populated the default prompt
        bots_with_prompt = Bot.objects.filter(avatar_prompt__isnull=False).count()
        total_bots = Bot.objects.count()

        # All bots should have a prompt (either custom or default)
        assert bots_with_prompt == total_bots

        # Check that the default prompt is present
        default_prompt = "Create a Bitmoji based on the given image. Accurately capture the person's facial features, but use a different hairstyle or hair color from the original image. Get rid of any accessories including earrings and glasses. Also, include only the face completely excluding the neck, shoulders, and body, and keep the facial expression neutral (neither smiling nor frowning). Make the output image square."

        # Check that our test bots have the expected prompts
        assert (
            self.bot_with_prompt.avatar_prompt
            == "Create a custom avatar with specific features"
        )
        assert self.bot_without_prompt.avatar_prompt == ""

        # If there are other bots in the database, they should have the default prompt
        other_bots = Bot.objects.exclude(
            id__in=[self.bot_with_prompt.id, self.bot_without_prompt.id],
        )
        if other_bots.exists():
            bots_with_default = other_bots.filter(avatar_prompt=default_prompt).count()
            assert bots_with_default > 0
