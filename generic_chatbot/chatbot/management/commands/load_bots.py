import json

from django.core.management.base import BaseCommand

from chatbot.models import Bot, Model


class Command(BaseCommand):
    help = "Load bots from config.json into the database"

    def handle(self, *args, **kwargs):
        try:
            # Ensure default models exist first
            self.stdout.write("Ensuring default models exist...")
            Model.get_or_create_default_models()
            self.stdout.write(self.style.SUCCESS("Default models loaded."))

            with open("config.json") as file:
                config_data = json.load(file)

            bots = config_data.get("bots", [])
            if not bots:
                self.stdout.write(self.style.WARNING("No bots found in config.json."))
                return

            for bot in bots:
                Bot.objects.update_or_create(
                    name=bot["name"],
                    defaults={
                        "prompt": bot["prompt"],
                    },
                )
            self.stdout.write(
                self.style.SUCCESS("Bots successfully loaded into the database."),
            )
        except Exception as e:
            self.stderr.write(f"Error loading bots: {e}")
