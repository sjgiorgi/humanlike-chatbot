from django.db import models

class Conversation(models.Model):
    conversation_id = models.CharField(max_length=255, unique=True)  # Conversation ID
    bot_name = models.CharField(max_length=255, default ="DefaultBot") # Bot Name
    participant_id = models.CharField(max_length=255)
    initial_utterance = models.CharField(max_length=255, null=True, blank=True)
    study_name = models.CharField(max_length=255, null=True, blank=True)
    user_group = models.CharField(max_length=255, null=True, blank=True)
    survey_id = models.CharField(max_length=255, null=True, blank=True)  # Survey ID
    survey_meta_data = models.TextField(null=True, blank=True)  # Survey metadata (can be long)
    started_time = models.DateTimeField(auto_now_add=True)  # Start time

    def __str__(self):
        return f"Conversation {self.conversation_id} started at {self.started_time}"

class Utterance(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="utterances",null=True, blank=True)   # Unique identifier per conversation
    speaker_id = models.CharField(max_length=255)       # 'participant' or 'bot'
    bot_name = models.CharField(max_length=255,null=True, blank=True)  
    participant_id = models.CharField(max_length=255,null=True, blank=True)  
    created_time = models.DateTimeField(auto_now_add=True)               # Timestamp
    text = models.TextField()      

    #new fields added for voice chat
    audio_file = models.FileField(upload_to="utterance_audio/", null=True, blank=True)  # path to saved audio
    is_voice = models.BooleanField(default=False)  # to distinguish voice vs text utterances

    def __str__(self):
        return f"{self.speaker_id}: {self.text[:50]}"


class Bot(models.Model):
    name = models.CharField(max_length=255, unique=True, default="DefaultBotName")  # Make name the unique identifier
    prompt = models.TextField()  # Bot's prompt
    model_type = models.CharField(max_length=255, default="OpenAI")  # Model type (e.g., OpenAI, Anthropic)
    model_id = models.CharField(max_length=255, default="gpt-4")  # Model ID, optional
    initial_utterance = models.TextField(blank=True, null=True)

    # New Column:
    AVATAR_CHOICES = [
        ('none', 'None'),
        ('default', 'Default'),
        ('user', 'User Provided'),
    ]
    avatar_type = models.CharField(max_length=20, choices=AVATAR_CHOICES, default="none")

    def __str__(self):
        return self.name

class Keystroke(models.Model):
    conversation_id = models.CharField(max_length=255)  # Respnose_ID but not FK to conversation because keystroke logging can happen without conversation registration
    total_time_on_page = models.FloatField()
    total_time_away_from_page = models.FloatField()
    keystroke_count = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=False)

    def __str__(self):
        return f"Keystroke log for conversation {self.conversation_id} at {self.timestamp}"

class Avatar(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="avatars",null=True, blank=True)
    bot_conversation = models.CharField(max_length=255, null=True, blank=True)
    image = models.ImageField(upload_to='bot_avatars/', null=True, blank=True)
    def __str__(self):
        return f"Avatar for Conversation {self.bot.name} {self.bot.avatar_type} {self.image}"