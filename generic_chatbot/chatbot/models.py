from django.db import models


class Persona(models.Model):
    name = models.CharField(max_length=255, unique=True)
    instructions = models.TextField(help_text="Instructions for this persona")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Conversation(models.Model):
    conversation_id = models.CharField(max_length=255, unique=True)  # Conversation ID
    bot_name = models.CharField(max_length=255, default="DefaultBot")  # Bot Name
    participant_id = models.CharField(max_length=255)
    initial_utterance = models.CharField(max_length=255, null=True, blank=True)
    study_name = models.CharField(max_length=255, null=True, blank=True)
    user_group = models.CharField(max_length=255, null=True, blank=True)
    survey_id = models.CharField(max_length=255, null=True, blank=True)  # Survey ID
    survey_meta_data = models.TextField(
        null=True, blank=True,
    )  # Survey metadata (can be long)
    started_time = models.DateTimeField(auto_now_add=True)  # Start time
    
    # Track which persona was randomly selected for this conversation
    selected_persona = models.ForeignKey(
        Persona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
        help_text="The persona randomly selected for this conversation"
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
        upload_to="utterance_audio/", null=True, blank=True,
    )  # path to saved audio
    # to distinguish voice vs text utterances
    is_voice = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.speaker_id}: {self.text[:50]}"


class Bot(models.Model):
    # Make name the unique identifier
    name = models.CharField(max_length=255, unique=True, default="DefaultBotName")
    prompt = models.TextField()  # Bot's prompt
    # Model type (e.g., OpenAI, Anthropic)
    model_type = models.CharField(max_length=255, default="OpenAI")
    model_id = models.CharField(max_length=255, default="gpt-4")  # Model ID, optional
    initial_utterance = models.TextField(blank=True, null=True)

    # New Column:
    AVATAR_CHOICES = [
        ("none", "None"),
        ("default", "Default"),
        ("user", "User Provided"),
    ]
    avatar_type = models.CharField(
        max_length=20, choices=AVATAR_CHOICES, default="none",
    )
    
    # Message chunking control (bot-specific)
    chunk_messages = models.BooleanField(
        default=True,
        help_text="If true, split responses into human-like chunks; if false, send as one blob",
    )

    # Many-to-many relationship with personas
    personas = models.ManyToManyField(
        Persona,
        blank=True,
        related_name="bots",
        help_text="Select personas that this bot should embody"
    )

    def __str__(self):
        return self.name


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
        Bot, on_delete=models.CASCADE, related_name="avatars", null=True, blank=True,
    )
    bot_conversation = models.CharField(max_length=255, null=True, blank=True)
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, default="similar",
    )
    participant_avatar = models.TextField(null=True, blank=True)
    chatbot_avatar = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Avatar for Conversation {self.bot.name} {self.bot.avatar_type} {self.condition} {self.participant_avatar} {self.chatbot_avatar}"


class Control(models.Model):
    chunk_messages = models.BooleanField(
        default=True,
        help_text="If true, split into human-like chunks; if false, send as one blob",
    )

    def __str__(self):
        return f"Chunks {'on' if self.chunk_messages else 'off'}"
