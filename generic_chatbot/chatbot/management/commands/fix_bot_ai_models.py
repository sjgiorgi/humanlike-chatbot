from django.core.management.base import BaseCommand

from chatbot.models import Bot, Model, ModelProvider


class Command(BaseCommand):
    help = "Fix existing bots that have issues with their ai_model field"

    def handle(self, *args, **options):
        # Get or create OpenAI provider
        openai_provider, created = ModelProvider.objects.get_or_create(
            name="OpenAI",
            defaults={
                "display_name": "OpenAI",
                "description": "OpenAI's language models including GPT series",
            },
        )
        if created:
            self.stdout.write(f"Created OpenAI provider: {openai_provider}")

        # Get or create gpt-4o-mini model
        gpt4o_mini_model, created = Model.objects.get_or_create(
            provider=openai_provider,
            model_id="gpt-4o-mini",
            defaults={
                "display_name": "GPT-4o Mini",
                "capabilities": ["Chat", "Vision", "Audio", "Reasoning"],
            },
        )
        if created:
            self.stdout.write(f"Created GPT-4o Mini model: {gpt4o_mini_model}")

        # Get all bots
        all_bots = Bot.objects.all()
        self.stdout.write(f"Checking {all_bots.count()} bots for ai_model issues...")

        fixed_count = 0
        for bot in all_bots:
            needs_update = False
            update_reason = ""

            # Check if bot has no ai_model
            if bot.ai_model is None:
                update_reason = (
                    f"Bot '{bot.name}' has no ai_model, setting to gpt-4o-mini"
                )
                bot.ai_model = gpt4o_mini_model
                needs_update = True

            # Check if bot's ai_model points to a non-existent model
            elif bot.ai_model_id is not None:
                try:
                    # Try to access the ai_model to see if it exists
                    _ = bot.ai_model
                except Model.DoesNotExist:
                    update_reason = f"Bot '{bot.name}' has invalid ai_model_id {bot.ai_model_id}, setting to gpt-4o-mini"
                    bot.ai_model = gpt4o_mini_model
                    needs_update = True

            # Check if bot has old model_type/model_id but no proper ai_model
            if bot.model_type and bot.model_id and bot.ai_model is None:
                self.stdout.write(
                    f"Bot '{bot.name}' has model_type='{bot.model_type}' and model_id='{bot.model_id}' but no ai_model",
                )
                # Try to find matching model
                matching_model = Model.objects.filter(
                    provider__name=bot.model_type,
                    model_id=bot.model_id,
                ).first()

                if matching_model:
                    update_reason = (
                        f"Found matching model for bot '{bot.name}', setting ai_model"
                    )
                    bot.ai_model = matching_model
                else:
                    update_reason = f"No matching model found for bot '{bot.name}', setting to gpt-4o-mini"
                    bot.ai_model = gpt4o_mini_model
                needs_update = True

            if needs_update:
                bot.save()
                self.stdout.write(self.style.SUCCESS(update_reason))
                fixed_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished! Fixed {fixed_count} bots out of {all_bots.count()} total bots.",
            ),
        )
