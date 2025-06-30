import json
from django.db import connection
from django.apps import apps

def load_config():
    """
    Load the configuration from config.json and add bots to the database only if they do not exist.
    """
    try:
        # Load the JSON file
        with open("config.json", "r") as file:
            config = json.load(file)

        # Check if "bots" exists in the configuration
        bots = config.get("bots", [])
        if not bots:
            print("No bots found in configuration.")
            return config

        # Check if the database is ready
        if not connection.introspection.table_names():
            print("Database not ready. Skipping bot loading.")
            return config

        # Dynamically fetch the Bot model
        Bot = apps.get_model("chatbot", "Bot")  # chatbot is your app name

        # Get existing bot names from the database
        existing_bots = set(Bot.objects.values_list("name", flat=True))

        # Add bots only if they are not already in the database
        for bot in bots:
            if bot["name"] not in existing_bots:
                if "model_type" not in bot or "model_id" not in bot:
                    raise ValueError(f"Bot '{bot['name']}' is missing required 'model_type' or 'model_id'.")
                
                Bot.objects.create(
                    name=bot["name"], 
                    prompt=bot["prompt"],
                    model_type=bot["model_type"],  # Ensure model_type is set
                    model_id=bot["model_id"]  # Ensure model_id is set
                )
        
        print("Bots loaded successfully.")
        return config
    
    except FileNotFoundError:
        raise RuntimeError("Configuration file 'config.json' not found.")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error decoding 'config.json': {e}")
    except Exception as e:
        print(f"Unexpected error loading config: {e}")
        raise
