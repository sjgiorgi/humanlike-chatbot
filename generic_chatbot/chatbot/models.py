from django.db import models


class Persona(models.Model):
    name = models.CharField(max_length=255, unique=True)
    instructions = models.TextField(help_text="Instructions for this persona")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Conversation(models.Model):
    conversation_id = models.CharField(max_length=255, unique=True)  # Conversation ID
    bot_name = models.CharField(max_length=255, default="DefaultBot")  # Bot Name
    participant_id = models.CharField(max_length=255)
    initial_utterance = models.CharField(max_length=255, null=True, blank=True)
    study_name = models.CharField(max_length=255, null=True, blank=True)
    user_group = models.CharField(max_length=255, null=True, blank=True)
    survey_id = models.CharField(max_length=255, null=True, blank=True)  # Survey ID
    survey_meta_data = models.TextField(
        null=True,
        blank=True,
    )  # Survey metadata (can be long)
    started_time = models.DateTimeField(auto_now_add=True)  # Start time

    # Track which persona was randomly selected for this conversation
    selected_persona = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
        help_text="The persona randomly selected for this conversation",
    )

    def __str__(self):
        return f"Conversation {self.conversation_id} started at {self.started_time}"


class Utterance(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        # Unique identifier per conversation
        related_name="utterances",
        null=True,
        blank=True,
    )
    speaker_id = models.CharField(max_length=255)  # 'participant' or 'bot'
    bot_name = models.CharField(max_length=255, null=True, blank=True)
    participant_id = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True)  # Timestamp
    text = models.TextField()

    # new fields added for voice chat
    audio_file = models.FileField(
        upload_to="utterance_audio/",
        null=True,
        blank=True,
    )  # path to saved audio
    # to distinguish voice vs text utterances
    is_voice = models.BooleanField(default=False)

    # Store the instruction prompt that was passed to the LLM for this utterance
    instruction_prompt = models.TextField(
        null=True,
        blank=True,
        help_text="The instruction prompt (bot prompt + persona) that was passed to the LLM for this utterance",
    )

    # Store the chat history that was passed to the LLM for this utterance
    chat_history_used = models.TextField(
        null=True,
        blank=True,
        help_text="The chat history (formatted as JSON) that was actually passed to the LLM for this utterance",
    )

    def __str__(self):
        return f"{self.speaker_id}: {self.text[:50]}"


class ModelProvider(models.Model):
    """Model provider (e.g., OpenAI, Anthropic)"""

    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    class Meta:
        ordering = ["name"]

    @classmethod
    def get_or_create_default_providers(cls):
        """Create default providers if they don't exist"""
        providers_data = {
            "OpenAI": {
                "display_name": "OpenAI",
                "description": "OpenAI's language models including GPT series",
            },
            "Anthropic": {
                "display_name": "Anthropic",
                "description": "Anthropic's Claude language models",
            },
        }

        providers = {}
        for name, data in providers_data.items():
            provider, created = cls.objects.get_or_create(
                name=name,
                defaults=data,
            )
            providers[name] = provider
        return providers


class Model(models.Model):
    """AI model with capabilities and provider relationship"""

    provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.CASCADE,
        related_name="models",
    )
    model_id = models.CharField(
        max_length=255,
        help_text="The actual model ID used by the provider",
    )
    display_name = models.CharField(max_length=255, help_text="Human-readable name")
    description = models.TextField(blank=True)
    capabilities = models.JSONField(
        default=list,
        help_text="List of capabilities like ['Chat', 'Reasoning', 'Code']",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider.display_name} - {self.display_name}"

    class Meta:
        unique_together = ["provider", "model_id"]
        ordering = ["provider__name", "display_name"]

    @classmethod
    def get_or_create_default_models(cls):
        """Create default models if they don't exist"""
        # First ensure providers exist
        providers = ModelProvider.get_or_create_default_providers()

        models_data = {
            "OpenAI": [
                {
                    "model_id": "gpt-5",
                    "display_name": "GPT-5",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "gpt-5-mini",
                    "display_name": "GPT-5 Mini",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "gpt-5-nano",
                    "display_name": "GPT-5 Nano",
                    "capabilities": ["Chat", "Basic Reasoning", "Code"],
                },
                {
                    "model_id": "gpt-4o",
                    "display_name": "GPT-4o",
                    "capabilities": ["Chat", "Vision", "Audio", "Reasoning"],
                },
                {
                    "model_id": "gpt-4o-mini",
                    "display_name": "GPT-4o Mini",
                    "capabilities": ["Chat", "Vision", "Audio", "Reasoning"],
                },
                {
                    "model_id": "gpt-4.1",
                    "display_name": "GPT-4.1",
                    "capabilities": ["Chat", "Reasoning", "Analysis"],
                },
                {
                    "model_id": "gpt-4.1-mini",
                    "display_name": "GPT-4.1 Mini",
                    "capabilities": ["Chat", "Reasoning", "Analysis"],
                },
                {
                    "model_id": "gpt-4.1-nano",
                    "display_name": "GPT-4.1 Nano",
                    "capabilities": ["Chat", "Basic Reasoning"],
                },
                {
                    "model_id": "gpt-3.5-turbo",
                    "display_name": "GPT-3.5 Turbo",
                    "capabilities": ["Chat", "Code", "Analysis"],
                },
            ],
            "Anthropic": [
                {
                    "model_id": "claude-opus-4-1-20250805",
                    "display_name": "Claude Opus 4.1",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "claude-opus-4-20250514",
                    "display_name": "Claude Opus 4",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "claude-sonnet-4-20250514",
                    "display_name": "Claude Sonnet 4",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "claude-3-5-sonnet-20241022",
                    "display_name": "Claude 3.5 Sonnet",
                    "capabilities": ["Chat", "Reasoning", "Code", "Analysis"],
                },
                {
                    "model_id": "claude-3-5-haiku-20241022",
                    "display_name": "Claude 3.5 Haiku",
                    "capabilities": ["Chat", "Basic Reasoning", "Code"],
                },
                {
                    "model_id": "claude-3-haiku-20240307",
                    "display_name": "Claude 3 Haiku",
                    "capabilities": ["Chat", "Basic Reasoning", "Code"],
                },
            ],
        }

        created_models = []
        for provider_name, models_list in models_data.items():
            provider = providers[provider_name]
            for model_data in models_list:
                model, created = cls.objects.get_or_create(
                    provider=provider,
                    model_id=model_data["model_id"],
                    defaults={
                        "display_name": model_data["display_name"],
                        "capabilities": model_data["capabilities"],
                    },
                )
                if created:
                    created_models.append(model)

        return created_models


class Bot(models.Model):
    # Make name the unique identifier
    name = models.CharField(max_length=255, unique=True, default="DefaultBotName")
    prompt = models.TextField()  # Bot's prompt
    # Use foreign key to Model instead of separate model_type and model_id
    # Keep old fields for migration compatibility
    model_type = models.CharField(
        max_length=255,
        default="OpenAI",
        null=True,
        blank=True,
    )
    model_id = models.CharField(max_length=255, default="gpt-4o-mini", null=True, blank=True)
    ai_model = models.ForeignKey(
        Model, 
        on_delete=models.CASCADE, 
        related_name="bots",
        null=False,
        blank=False
    )
    initial_utterance = models.TextField(blank=True, null=True)

    # New Column:
    AVATAR_CHOICES = [
        ("none", "None"),
        ("default", "Default"),
        ("user", "User Provided"),
    ]
    avatar_type = models.CharField(
        max_length=20,
        choices=AVATAR_CHOICES,
        default="none",
    )

    # Message chunking control (bot-specific)
    chunk_messages = models.BooleanField(
        default=True,
        help_text="If true, split responses into human-like chunks; if false, send as one blob",
    )

    # Humanlike delay control (bot-specific)
    humanlike_delay = models.BooleanField(
        default=True,
        help_text="If true, apply human-like typing delays; if false, show messages instantly",
    )

    # Humanlike delay configuration (bot-specific)
    typing_speed_min_ms = models.IntegerField(
        default=100,
        help_text="Minimum milliseconds per character for typing speed (base delay)",
    )
    typing_speed_max_ms = models.IntegerField(
        default=200,
        help_text="Maximum milliseconds per character for typing speed (base delay)",
    )
    question_thinking_ms = models.IntegerField(
        default=300,
        help_text="Additional milliseconds for chunks containing questions",
    )
    first_chunk_thinking_ms = models.IntegerField(
        default=600,
        help_text="Additional milliseconds for the first chunk (thinking time)",
    )
    last_chunk_pause_ms = models.IntegerField(
        default=100,
        help_text="Additional milliseconds for the last chunk",
    )
    min_delay_ms = models.IntegerField(
        default=200,
        help_text="Minimum delay in milliseconds (when backend is fast)",
    )
    max_delay_ms = models.IntegerField(
        default=800,
        help_text="Maximum delay in milliseconds (when backend is slow)",
    )

    # Follow-up on idle settings
    follow_up_on_idle = models.BooleanField(
        default=False,
        help_text="If true, bot will send follow-up messages when user is idle",
    )
    idle_time_minutes = models.IntegerField(
        default=2,
        help_text="Minutes of inactivity before considering user idle",
    )
    follow_up_instruction_prompt = models.TextField(
        blank=True,
        null=True,
        help_text="Instructions for generating follow-up messages when user is idle",
    )
    recurring_followup = models.BooleanField(
        default=False,
        help_text="If true, bot will keep sending follow-up messages while user is idle. If false, bot will only send one follow-up per idle period.",
    )

    # Transcript length control
    max_transcript_length = models.IntegerField(
        default=0,
        help_text="Maximum number of messages to include in chat history. 0 = no chat history (only current message), 1+ = include that many most recent messages, negative = unlimited history.",
    )

    # Many-to-many relationship with personas
    personas = models.ManyToManyField(
        Persona,
        blank=True,
        related_name="bots",
        help_text="Select personas that this bot should embody",
    )

    def __str__(self):
        return self.name

    @classmethod
    def get_default_model(cls):
        """Get or create a default model for bots"""
        # Ensure default models exist
        Model.get_or_create_default_models()

        # Return the first available model (preferably GPT-4o Mini)
        try:
            return (
                Model.objects.filter(
                    provider__name="OpenAI",
                    model_id="gpt-4o-mini",
                ).first()
                or Model.objects.first()
            )
        except Exception:
            return None


class Keystroke(models.Model):
    # Respnose_ID but not FK to conversation because keystroke logging can happen without conversation registration
    conversation_id = models.CharField(max_length=255)
    total_time_on_page = models.FloatField()
    total_time_away_from_page = models.FloatField()
    keystroke_count = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=False)

    def __str__(self):
        return (
            f"Keystroke log for conversation {self.conversation_id} at {self.timestamp}"
        )


class Avatar(models.Model):
    # New Column:
    CONDITION_CHOICES = [
        ("control", "control"),
        ("similar", "similar"),
        ("dissimilar", "dissimilar"),
    ]
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
        related_name="avatars",
        null=True,
        blank=True,
    )
    bot_conversation = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="similar",
    )
    participant_avatar = models.TextField(null=True, blank=True)
    chatbot_avatar = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Avatar for Conversation {self.bot.name} {self.bot.avatar_type} {self.condition} {self.participant_avatar} {self.chatbot_avatar}"
