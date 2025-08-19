# Generated manually to populate ai_model for existing bots

from django.db import migrations


def populate_ai_model_for_existing_bots(apps, schema_editor):
    """Populate ai_model field for existing Bot records that don't have it set"""
    Bot = apps.get_model('chatbot', 'Bot')
    Model = apps.get_model('chatbot', 'Model')
    ModelProvider = apps.get_model('chatbot', 'ModelProvider')
    
    # Get or create OpenAI provider
    openai_provider, _ = ModelProvider.objects.get_or_create(
        name='OpenAI',
        defaults={
            'display_name': 'OpenAI',
            'description': "OpenAI's language models including GPT series"
        }
    )
    
    # Get or create gpt-4o-mini model
    gpt4o_mini_model, _ = Model.objects.get_or_create(
        provider=openai_provider,
        model_id='gpt-4o-mini',
        defaults={
            'display_name': 'GPT-4o Mini',
            'capabilities': ['Chat', 'Vision', 'Audio', 'Reasoning']
        }
    )
    
    # Update all bots that don't have an ai_model set
    bots_without_ai_model = Bot.objects.filter(ai_model__isnull=True)
    print(f"Found {bots_without_ai_model.count()} bots without ai_model, updating them...")
    bots_without_ai_model.update(ai_model=gpt4o_mini_model)
    
    # Also update bots that have ai_model but it might be pointing to a non-existent model
    bots_with_invalid_ai_model = Bot.objects.filter(ai_model__isnull=False)
    for bot in bots_with_invalid_ai_model:
        try:
            # Test if the ai_model is valid by accessing it
            _ = bot.ai_model
        except:
            # If accessing ai_model fails, update it to gpt-4o-mini
            bot.ai_model = gpt4o_mini_model
            bot.save()


def reverse_populate_ai_model_for_existing_bots(apps, schema_editor):
    """Reverse operation - this is a no-op since we can't safely remove ai_model"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0024_alter_bot_model_id'),
    ]

    operations = [
        migrations.RunPython(
            populate_ai_model_for_existing_bots,
            reverse_populate_ai_model_for_existing_bots
        ),
    ]
