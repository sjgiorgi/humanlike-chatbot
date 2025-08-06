from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Bot, Control, Conversation, Keystroke, Utterance


class BaseAdmin(admin.ModelAdmin):
    """Base admin class with common styling and functionality"""
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
    
    def get_list_display(self, request):
        """Add custom styling to list display"""
        list_display = super().get_list_display(request)
        return list_display


@admin.register(Control)
class ControlAdmin(BaseAdmin):
    list_display = ("chunk_messages",)
    actions = None

    def has_add_permission(self, request):
        # only allow creating the very first row
        return not Control.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # prevent deletion
        return False


@admin.register(Conversation)
class ConversationAdmin(BaseAdmin):
    list_display = (
        "conversation_id",
        "bot_name",
        "participant_id",
        "utterance_count",
        "study_name",
        "user_group",
        "started_time",
    )
    list_display_links = ("conversation_id",)
    search_fields = (
        "conversation_id",
        "bot_name",
        "participant_id",
        "study_name",
        "user_group",
        "survey_id",
    )
    list_filter = ("bot_name", "user_group", "study_name", "started_time")
    readonly_fields = ("started_time", "utterance_count")
    ordering = ("-started_time",)
    list_per_page = 25
    
    def utterance_count(self, obj):
        count = obj.utterances.count()
        if count > 0:
            url = reverse('admin:chatbot_utterance_changelist') + f'?conversation__id__exact={obj.id}'
            return format_html('<a href="{}" class="utterance-link">{} utterances</a>', url, count)
        return format_html('<span class="no-utterances">0 utterances</span>')
    utterance_count.short_description = "Messages"

    fieldsets = (
        ("Basic Information", {
            "fields": ("conversation_id", "bot_name", "participant_id", "initial_utterance")
        }),
        ("Study Information", {
            "fields": ("study_name", "user_group", "survey_id"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("survey_meta_data", "started_time"),
            "classes": ("collapse",)
        }),
    )


@admin.register(Utterance)
class UtteranceAdmin(BaseAdmin):
    list_display = (
        "conversation_link",
        "speaker_id",
        "bot_name",
        "participant_id",
        "text_preview",
        "created_time",
        "is_voice",
    )
    list_display_links = ("conversation_link", "text_preview")
    search_fields = ("speaker_id", "bot_name", "participant_id", "text", "conversation__conversation_id")
    list_filter = ("is_voice", "speaker_id", "bot_name", "created_time")
    readonly_fields = ("created_time",)
    ordering = ("-created_time",)
    list_per_page = 50
    
    def conversation_link(self, obj):
        if obj.conversation:
            url = reverse('admin:chatbot_conversation_change', args=[obj.conversation.id])
            return format_html('<a href="{}" class="conversation-link">{}</a>', url, obj.conversation.conversation_id)
        return format_html('<span class="no-conversation">No conversation</span>')
    conversation_link.short_description = "Conversation ID"
    
    def text_preview(self, obj):
        preview = obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
        speaker_class = "user-message" if obj.speaker_id == "user" else "bot-message"
        return format_html('<span class="message-preview {}" title="{}">{}</span>', speaker_class, obj.text, preview)
    text_preview.short_description = "Message"

    fieldsets = (
        ("Message Content", {
            "fields": ("conversation", "speaker_id", "text")
        }),
        ("Participant Information", {
            "fields": ("bot_name", "participant_id"),
            "classes": ("collapse",)
        }),
        ("Voice Settings", {
            "fields": ("audio_file", "is_voice"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_time",),
            "classes": ("collapse",)
        }),
    )


@admin.register(Bot)
class BotAdmin(BaseAdmin):
    list_display = (
        "name",
        "model_type",
        "model_id",
        "avatar_type",
        "has_initial_utterance",
    )
    list_display_links = ("name",)
    search_fields = ("name", "model_type", "model_id")
    list_filter = ("model_type", "avatar_type")
    ordering = ("name",)
    
    def has_initial_utterance(self, obj):
        return bool(obj.initial_utterance and obj.initial_utterance.strip())
    has_initial_utterance.boolean = True
    has_initial_utterance.short_description = "Has Initial Message"

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "model_type", "model_id")
        }),
        ("Configuration", {
            "fields": ("prompt", "initial_utterance", "avatar_type")
        }),
    )


@admin.register(Keystroke)
class KeystrokeAdmin(BaseAdmin):
    list_display = (
        "conversation_id",
        "timestamp",
        "keystroke_count",
        "total_time_on_page",
        "total_time_away_from_page",
        "total_session_time",
    )
    list_display_links = ("conversation_id",)
    search_fields = ("conversation_id",)
    list_filter = ("timestamp",)
    ordering = ("-timestamp",)
    readonly_fields = ("timestamp",)
    list_per_page = 25
    
    def total_session_time(self, obj):
        total = obj.total_time_on_page + obj.total_time_away_from_page
        return format_html('<span class="session-time">{:.1f}s</span>', total)
    total_session_time.short_description = "Total Session"

    fieldsets = (
        ("Session Information", {
            "fields": ("conversation_id", "timestamp")
        }),
        ("Timing Data", {
            "fields": ("total_time_on_page", "total_time_away_from_page", "keystroke_count")
        }),
    )
