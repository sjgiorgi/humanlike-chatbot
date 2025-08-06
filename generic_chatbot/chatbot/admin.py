from django.contrib import admin

from .models import Bot, Control, Conversation, Keystroke, Utterance


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = ("chunk_messages",)
    actions = None

    def has_add_permission(self, request):
        # only allow creating the very first row
        return not Control.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # prevent deletion
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "conversation_id",
        "bot_name",
        "participant_id",
        "initial_utterance",
        "study_name",
        "user_group",
        "survey_id",
        "started_time",
    )
    search_fields = (
        "conversation_id",
        "bot_name",
        "participant_id",
        "study_name",
        "user_group",
        "survey_id",
    )
    list_filter = ("bot_name", "user_group")
    readonly_fields = ("started_time",)


@admin.register(Utterance)
class UtteranceAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "speaker_id",
        "bot_name",
        "participant_id",
        "created_time",
        "is_voice",
    )
    search_fields = ("speaker_id", "bot_name", "participant_id", "text")
    list_filter = ("is_voice", "speaker_id", "bot_name")
    readonly_fields = ("created_time",)


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ("name", "model_type", "model_id")
    search_fields = ("name", "model_type", "model_id")


@admin.register(Keystroke)
class KeystrokeAdmin(admin.ModelAdmin):
    list_display = (
        "conversation_id",
        "timestamp",
        "keystroke_count",
        "total_time_on_page",
        "total_time_away_from_page",
    )
    search_fields = ("conversation_id",)
    list_filter = ("timestamp",)
