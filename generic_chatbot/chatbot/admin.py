import io
import logging
import time
import uuid

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from PIL import Image

from .models import (
    Avatar,
    Bot,
    Conversation,
    Keystroke,
    ModerationSettings,
    Persona,
    Utterance,
)
from .services.avatar import generate_avatar
from .services.s3_helper import delete, get_presigned_url, upload

# Get logger for this module
logger = logging.getLogger(__name__)


class AvatarImageField(forms.FileField):
    """Custom form field for avatar image upload with validation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.attrs.update(
            {
                "accept": "image/*",
                "class": "avatar-upload-field",
            },
        )

    def clean(self, data, initial=None):
        """Validate and process uploaded image"""
        if not data:
            return initial

        # Validate file type
        if not data.content_type.startswith("image/"):
            raise ValidationError("Please upload a valid image file.")

        # Validate file size (max 5MB)
        if data.size > 5 * 1024 * 1024:
            raise ValidationError("Image file size must be less than 5MB.")

        return data


class BotAdminForm(forms.ModelForm):
    """Custom form for Bot admin with avatar upload functionality"""

    avatar_image = AvatarImageField(
        required=False,
        help_text="Upload an image for the bot avatar. Will be processed and stored in S3.",
    )

    remove_avatar = forms.BooleanField(
        required=False,
        label="Remove Avatar",
        help_text="Check this box to remove the current avatar and set avatar type to 'none'.",
    )

    class Meta:
        model = Bot
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        ai_model = cleaned_data.get("ai_model")

        if not ai_model:
            raise ValidationError(
                {
                    "ai_model": "A model must be selected. Bots cannot function without a model.",
                },
            )

        # Validate follow-up configuration
        follow_up_on_idle = cleaned_data.get("follow_up_on_idle")
        follow_up_instruction_prompt = cleaned_data.get(
            "follow_up_instruction_prompt")

        if follow_up_on_idle and not follow_up_instruction_prompt:
            raise ValidationError(
                {
                    "follow_up_instruction_prompt": "Follow-up instruction prompt is required when follow-up is enabled.",
                },
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Show current avatar if exists
            try:
                from .models import Avatar

                avatar = Avatar.objects.filter(
                    bot=self.instance,
                    bot_conversation__isnull=True,
                ).first()
                if avatar and avatar.chatbot_avatar:
                    # Check if we're in local development
                    import os

                    is_local = os.getenv("BACKEND_ENVIRONMENT") == "local"

                    if is_local:
                        # For local development, serve from media directory
                        from pathlib import Path

                        from django.conf import settings

                        local_path = (
                            Path(settings.MEDIA_ROOT)
                            / "avatars"
                            / avatar.chatbot_avatar
                        )
                        if local_path.exists():
                            image_url = f"/media/avatars/{avatar.chatbot_avatar}"
                            self.fields["avatar_image"].help_text = format_html(
                                '<div class="current-avatar-section"><strong>Current Avatar:</strong><br>'
                                '<img src="{}" alt="Current Avatar" class="current-avatar" /><br>'
                                "<small>{}</small></div>",
                                image_url,
                                avatar.chatbot_avatar,
                            )
                        else:
                            self.fields[
                                "avatar_image"
                            ].help_text = f"Current avatar: {avatar.chatbot_avatar} (file not found)"
                    else:
                        # Production: Get presigned URL for current avatar
                        image_url = get_presigned_url(
                            "avatar",
                            avatar.chatbot_avatar,
                            expiration=3600,
                        )
                        if image_url:
                            self.fields["avatar_image"].help_text = format_html(
                                '<div class="current-avatar-section"><strong>Current Avatar:</strong><br>'
                                '<img src="{}" alt="Current Avatar" class="current-avatar" /><br>'
                                "<small>{}</small></div>",
                                image_url,
                                avatar.chatbot_avatar,
                            )
                        else:
                            self.fields[
                                "avatar_image"
                            ].help_text = f"Current avatar: {avatar.chatbot_avatar}"

                    # Show remove avatar option only when there's an existing avatar
                else:
                    # Hide remove avatar option if no avatar exists
                    self.fields["remove_avatar"].widget = forms.HiddenInput()
            except Exception:
                # Hide remove avatar option on error
                self.fields["remove_avatar"].widget = forms.HiddenInput()
        else:
            # Hide remove avatar option for new bots
            self.fields["remove_avatar"].widget = forms.HiddenInput()


class BaseAdmin(admin.ModelAdmin):
    """Base admin class with common styling and functionality"""

    class Media:
        css = {
            "all": ("admin/css/custom_admin.css",),
        }

    def get_list_display(self, request):
        """Add custom styling to list display"""
        list_display = super().get_list_display(request)
        return list_display


@admin.register(Persona)
class PersonaAdmin(BaseAdmin):
    list_display = (
        "name",
        "instructions_preview",
        "bot_count",
        "created_at",
        "updated_at",
    )
    list_display_links = ("name",)
    search_fields = ("name", "instructions")
    list_filter = ("created_at", "updated_at")
    ordering = ("name",)
    list_per_page = 25

    def instructions_preview(self, obj):
        preview = (
            obj.instructions[:100] + "..."
            if len(obj.instructions) > 100
            else obj.instructions
        )
        return format_html(
            '<span class="instructions-preview" title="{}">{}</span>',
            obj.instructions,
            preview,
        )

    instructions_preview.short_description = "Instructions"

    def bot_count(self, obj):
        count = obj.bots.count()
        if count > 0:
            url = (
                reverse("admin:chatbot_bot_changelist")
                + f"?personas__id__exact={obj.id}"
            )
            return format_html('<a href="{}" class="bot-link">{} bots</a>', url, count)
        return format_html('<span class="no-bots">0 bots</span>')

    bot_count.short_description = "Assigned Bots"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name",),
            },
        ),
        (
            "Instructions",
            {
                "fields": ("instructions",),
                "description": "Define the personality, behavior, and characteristics for this persona",
            },
        ),
    )


@admin.register(Conversation)
class ConversationAdmin(BaseAdmin):
    list_display = (
        "conversation_id",
        "bot_name",
        "participant_id",
        "utterance_count",
        "selected_persona",
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
    list_filter = (
        "bot_name",
        "user_group",
        "study_name",
        "started_time",
        "selected_persona",
    )
    readonly_fields = ("started_time", "utterance_count", "selected_persona")
    ordering = ("-started_time",)
    list_per_page = 25

    def utterance_count(self, obj):
        count = obj.utterances.count()
        if count > 0:
            url = (
                reverse("admin:chatbot_utterance_changelist")
                + f"?conversation__id__exact={obj.id}"
            )
            return format_html(
                '<a href="{}" class="utterance-link">{} utterances</a>',
                url,
                count,
            )
        return format_html('<span class="no-utterances">0 utterances</span>')

    utterance_count.short_description = "Messages"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "conversation_id",
                    "bot_name",
                    "participant_id",
                    "initial_utterance",
                ),
            },
        ),
        (
            "Persona Information",
            {
                "fields": ("selected_persona",),
                "description": "The persona randomly selected for this conversation",
            },
        ),
        (
            "Study Information",
            {
                "fields": ("study_name", "user_group", "survey_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("survey_meta_data", "started_time"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Utterance)
class UtteranceAdmin(BaseAdmin):
    list_display = (
        "conversation_link",
        "speaker_id",
        "bot_name",
        "participant_id",
        "text_preview",
        "instruction_prompt_preview",
        "chat_history_used_preview",
        "created_time",
        "is_voice",
    )
    list_display_links = ("conversation_link", "text_preview")
    search_fields = (
        "speaker_id",
        "bot_name",
        "participant_id",
        "text",
        "conversation__conversation_id",
    )
    list_filter = ("is_voice", "speaker_id", "bot_name", "created_time")
    readonly_fields = ("created_time",)
    ordering = ("-created_time",)
    list_per_page = 50

    def conversation_link(self, obj):
        if obj.conversation:
            url = reverse(
                "admin:chatbot_conversation_change",
                args=[obj.conversation.id],
            )
            return format_html(
                '<a href="{}" class="conversation-link">{}</a>',
                url,
                obj.conversation.conversation_id,
            )
        return format_html('<span class="no-conversation">No conversation</span>')

    conversation_link.short_description = "Conversation ID"

    def text_preview(self, obj):
        preview = obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
        speaker_class = "user-message" if obj.speaker_id == "user" else "bot-message"
        return format_html(
            '<span class="message-preview {}" title="{}">{}</span>',
            speaker_class,
            obj.text,
            preview,
        )

    text_preview.short_description = "Message"

    def instruction_prompt_preview(self, obj):
        if obj.instruction_prompt and obj.instruction_prompt.strip():
            preview = (
                obj.instruction_prompt[:100] + "..."
                if len(obj.instruction_prompt) > 100
                else obj.instruction_prompt
            )
            return preview
        return "No instruction prompt"

    instruction_prompt_preview.short_description = "Instruction Prompt"

    def chat_history_used_preview(self, obj):
        if obj.chat_history_used and obj.chat_history_used.strip():
            try:
                # Parse JSON to get message count
                import json

                history_data = json.loads(obj.chat_history_used)
                message_count = len(history_data)
                return f"{message_count} messages"
            except (json.JSONDecodeError, TypeError):
                return (
                    obj.chat_history_used[:50] + "..."
                    if len(obj.chat_history_used) > 50
                    else obj.chat_history_used
                )
        return "No chat history"

    chat_history_used_preview.short_description = "Chat History Used"

    fieldsets = (
        (
            "Message Content",
            {
                "fields": (
                    "conversation",
                    "speaker_id",
                    "text",
                    "instruction_prompt",
                    "chat_history_used",
                ),
                "description": "Message content, instruction prompt (bot prompt + persona), and chat history that was passed to the LLM. For followup messages, the followup instruction prompt is sent as an admin message, not included in the system prompt.",
            },
        ),
        (
            "Participant Information",
            {
                "fields": ("bot_name", "participant_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Voice Settings",
            {
                "fields": ("audio_file", "is_voice"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_time",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Bot)
class BotAdmin(BaseAdmin):
    form = BotAdminForm

    list_display = (
        "name",
        "model_provider",
        "model_name",
        "avatar_type",
        "has_initial_utterance",
        "chunk_messages",
        "humanlike_delay",
        "follow_up_on_idle",
        "recurring_followup",
        "max_transcript_length",
        "get_persona_count",
        "moderation_summary",
        "avatar_preview",
    )
    list_display_links = ("name",)
    search_fields = ("name", "ai_model__provider__name",
                     "ai_model__display_name")
    list_filter = (
        "ai_model__provider",
        "avatar_type",
        "chunk_messages",
        "humanlike_delay",
        "follow_up_on_idle",
        "recurring_followup",
        "personas",
    )
    ordering = ("name",)
    filter_horizontal = ["personas"]

    def model_provider(self, obj):
        return obj.ai_model.provider.display_name

    model_provider.short_description = "Provider"

    def model_name(self, obj):
        return obj.ai_model.display_name

    model_name.short_description = "Model"

    def get_persona_count(self, obj):
        return obj.personas.count()

    get_persona_count.short_description = "Personas Count"

    def has_initial_utterance(self, obj):
        return bool(obj.initial_utterance and obj.initial_utterance.strip())

    has_initial_utterance.boolean = True
    has_initial_utterance.short_description = "Has Initial Message"

    def avatar_preview(self, obj):
        """Display avatar preview in list view"""
        try:
            from .models import Avatar

            avatar = Avatar.objects.filter(
                bot=obj,
                bot_conversation__isnull=True,
            ).first()
            if avatar and avatar.chatbot_avatar:
                # Check if we're in local development
                from django.conf import settings

                is_local = settings.BACKEND_ENVIRONMENT == "local"

                if is_local:
                    # For local development, serve from media directory
                    from pathlib import Path

                    local_path = (
                        Path(settings.MEDIA_ROOT) /
                        "avatars" / avatar.chatbot_avatar
                    )
                    if local_path.exists():
                        image_url = f"/media/avatars/{avatar.chatbot_avatar}"
                        return format_html(
                            '<img src="{}" alt="Avatar" class="avatar-preview" title="{}" />',
                            image_url,
                            avatar.chatbot_avatar,
                        )
                else:
                    # Production: Get presigned URL for display
                    image_url = get_presigned_url(
                        "avatar",
                        avatar.chatbot_avatar,
                        expiration=3600,
                    )
                    if image_url:
                        return format_html(
                            '<img src="{}" alt="Avatar" class="avatar-preview" title="{}" />',
                            image_url,
                            avatar.chatbot_avatar,
                        )
        except Exception:
            pass
        return format_html('<span class="no-avatar">No avatar</span>')

    avatar_preview.short_description = "Avatar"

    def moderation_summary(self, obj):
        """Display moderation settings summary"""
        # Check if any values differ from defaults
        defaults = {
            "moderation_harassment": 0.50,
            "moderation_harassment_threatening": 0.10,
            "moderation_hate": 0.50,
            "moderation_hate_threatening": 0.10,
            "moderation_self_harm": 0.20,
            "moderation_self_harm_instructions": 0.50,
            "moderation_self_harm_intent": 0.70,
            "moderation_sexual": 0.50,
            "moderation_sexual_minors": 0.20,
            "moderation_violence": 0.70,
            "moderation_violence_graphic": 0.80,
        }

        custom_count = 0
        for field_name, default_value in defaults.items():
            current_value = float(getattr(obj, field_name))
            if current_value != default_value:
                custom_count += 1

        if custom_count == 0:
            return format_html('<span class="default-moderation">Using defaults</span>')
        else:
            return format_html(
                '<span class="custom-moderation">{} custom values</span>', custom_count,
            )

    moderation_summary.short_description = "Moderation"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "ai_model"),
            },
        ),
        (
            "Configuration",
            {
                "fields": ("prompt", "initial_utterance"),
            },
        ),
        (
            "Personas",
            {
                "fields": ("personas",),
                "description": "Select the personas this bot should embody. You can select multiple personas.",
            },
        ),
        (
            "Avatar Settings",
            {
                "fields": (
                    "avatar_type",
                    "avatar_prompt",
                    "avatar_image",
                    "remove_avatar",
                ),
                "description": "Configure avatar type, prompt, and upload avatar image",
            },
        ),
        (
            "Response Settings",
            {
                "fields": (
                    "chunk_messages",
                    "humanlike_delay",
                    "max_transcript_length",
                ),
                "description": "Control how bot responses are formatted and displayed. Max transcript length controls how many previous messages to include in chat history. 0 = no chat history (only current message), 1+ = include that many most recent messages.",
            },
        ),
        (
            "Humanlike Delay Configuration",
            {
                "fields": (
                    "reading_words_per_minute",
                    "reading_jitter_min",
                    "reading_jitter_max",
                    "reading_thinking_min",
                    "reading_thinking_max",
                    "writing_words_per_minute",
                    "writing_jitter_min",
                    "writing_jitter_max",
                    "writing_thinking_min",
                    "writing_thinking_max",
                    "intra_message_delay_min",
                    "intra_message_delay_max",
                    "min_reading_delay",
                ),
                "description": "Fine-tune the humanlike delay parameters. All values are in seconds. Reading parameters control delay before typing starts, writing parameters control typing speed, intra-message delays control pauses between message parts.",
                "classes": ("collapse",),
            },
        ),
        (
            "Follow-up Settings",
            {
                "fields": (
                    "follow_up_on_idle",
                    "idle_time_minutes",
                    "follow_up_instruction_prompt",
                    "recurring_followup",
                ),
                "description": "Configure automatic follow-up messages when users are idle. The follow-up instruction prompt is sent as an admin message to the LLM (not a user message) and cannot be empty when follow-up is enabled. Best practice: Write instructions that ask the bot to use available conversation context to write a natural follow-up message.",
            },
        ),
        (
            "Moderation Settings",
            {
                "fields": (
                    ("moderation_harassment", "moderation_harassment_threatening"),
                    ("moderation_hate", "moderation_hate_threatening"),
                    (
                        "moderation_self_harm",
                        "moderation_self_harm_instructions",
                        "moderation_self_harm_intent",
                    ),
                    ("moderation_sexual", "moderation_sexual_minors"),
                    ("moderation_violence", "moderation_violence_graphic"),
                ),
                "description": "Moderation thresholds for each category (0.0-1.0). Lower values = stricter moderation. Leave at defaults unless you need custom values.",
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """Handle avatar image upload and processing"""
        # Save the bot first
        super().save_model(request, obj, form, change)

        # Handle avatar image upload
        avatar_image = form.cleaned_data.get("avatar_image")
        if avatar_image:
            # If avatar_type is 'none' but an image is uploaded, set it to 'default'
            if obj.avatar_type == "none":
                obj.avatar_type = "default"
                obj.save()

            if obj.avatar_type in ["default", "user"]:
                try:
                    # Check if we're in local development
                    from django.conf import settings

                    is_local = settings.BACKEND_ENVIRONMENT == "local"

                    if is_local:
                        # Local development: Process image directly without S3
                        raw_image = Image.open(avatar_image)

                        # Process through generate_avatar directly
                        image = generate_avatar(
                            raw_image,
                            obj,
                            obj.avatar_type,
                        )
                        image_key = (
                            image.name
                            if hasattr(image, "name")
                            else f"{obj.name}_{int(time.time())}.png"
                        )

                        if image and image_key:
                            # For local development, save to local media directory
                            from pathlib import Path

                            from django.conf import settings

                            # Create media directory if it doesn't exist
                            media_dir = Path(settings.MEDIA_ROOT) / "avatars"
                            media_dir.mkdir(parents=True, exist_ok=True)

                            # Save processed image locally
                            local_path = media_dir / image_key
                            with open(local_path, "wb") as f:
                                f.write(image.read())

                            # Create or update Avatar record
                            from .models import Avatar

                            avatar, created = Avatar.objects.get_or_create(
                                bot=obj,
                                bot_conversation__isnull=True,
                                defaults={"chatbot_avatar": image_key},
                            )

                            if not created:
                                # Delete old avatar file if exists
                                if (
                                    avatar.chatbot_avatar
                                ):  # Check if there's an existing avatar
                                    old_path = media_dir / avatar.chatbot_avatar
                                    if old_path.exists():
                                        old_path.unlink()
                                avatar.chatbot_avatar = image_key
                                avatar.save()

                            self.message_user(
                                request,
                                f"Avatar uploaded and processed successfully (local): {image_key}",
                                level="SUCCESS",
                            )
                        else:
                            self.message_user(
                                request,
                                "Failed to process avatar image. Please try again.",
                                level="ERROR",
                            )
                    else:
                        # Production: Use S3 flow
                        # Step 1: Upload raw image to S3 first (like frontend does)
                        raw_filename = (
                            f"admin_upload_{uuid.uuid4().hex}_{avatar_image.name}"
                        )
                        raw_image_key = f"uploads/{raw_filename}"

                        # Convert uploaded file to PIL Image and upload to S3
                        raw_image = Image.open(avatar_image)
                        raw_image_bytes = io.BytesIO()
                        raw_image.save(raw_image_bytes, format="PNG")
                        raw_image_bytes.seek(0)

                        # Upload raw image to S3 (use direct S3 upload to avoid avatar prefix)
                        import os

                        from .services.s3_helper import s3

                        try:
                            s3.upload_fileobj(
                                raw_image_bytes,
                                os.getenv("AWS_BUCKET_NAME"),
                                raw_image_key,
                                ExtraArgs={
                                    "ContentType": "image/png",
                                    "ACL": "private",
                                },
                            )
                            logger.debug(
                                f"Successfully uploaded raw image to S3: {raw_image_key}",
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to upload raw image to S3: {e}")
                            raise RuntimeError(
                                f"Failed to upload raw image to S3: {e!s}",
                            )

                        # Step 2: Process through generate_avatar (like frontend does)
                        from .services.avatar import download

                        try:
                            processed_image = download("uploads", raw_filename)
                            if not processed_image:
                                raise RuntimeError(
                                    f"Failed to download image from S3: {raw_image_key}",
                                )
                            logger.debug(
                                f"Successfully downloaded image from S3: {raw_image_key}",
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to download image from S3: {e}")
                            # Clean up raw image on failure
                            s3.delete_object(
                                Bucket=os.getenv("AWS_BUCKET_NAME"),
                                Key=raw_image_key,
                            )
                            raise RuntimeError(
                                f"Failed to download image from S3: {e!s}",
                            )

                        if processed_image:
                            image = generate_avatar(
                                processed_image,
                                obj,
                                obj.avatar_type,
                            )
                            image_key = (
                                image.name
                                if hasattr(image, "name")
                                else f"{obj.name}_{int(time.time())}.png"
                            )

                            if image and image_key:
                                try:
                                    # Upload processed image to S3
                                    upload_result = upload(image, image_key)
                                    if not upload_result:
                                        raise RuntimeError(
                                            "S3 upload returned None")

                                    # Clean up raw image (use direct S3 delete to avoid avatar prefix)
                                    s3.delete_object(
                                        Bucket=os.getenv("AWS_BUCKET_NAME"),
                                        Key=raw_image_key,
                                    )

                                    # Create or update Avatar record
                                    from .models import Avatar

                                    avatar, created = Avatar.objects.get_or_create(
                                        bot=obj,
                                        bot_conversation__isnull=True,
                                        defaults={"chatbot_avatar": image_key},
                                    )

                                    if not created:
                                        # Delete old avatar from S3 if exists
                                        if avatar.chatbot_avatar:
                                            delete(
                                                "avatar", avatar.chatbot_avatar)
                                        avatar.chatbot_avatar = image_key
                                        avatar.save()

                                    self.message_user(
                                        request,
                                        f"Avatar uploaded and processed successfully: {image_key}",
                                        level="SUCCESS",
                                    )
                                except Exception as e:
                                    # Clean up raw image on failure
                                    s3.delete_object(
                                        Bucket=os.getenv("AWS_BUCKET_NAME"),
                                        Key=raw_image_key,
                                    )
                                    self.message_user(
                                        request,
                                        f"Failed to upload avatar to S3: {e!s}",
                                        level="ERROR",
                                    )
                            else:
                                # Clean up raw image on failure
                                s3.delete_object(
                                    Bucket=os.getenv("AWS_BUCKET_NAME"),
                                    Key=raw_image_key,
                                )
                                self.message_user(
                                    request,
                                    "Failed to process avatar image. Please try again.",
                                    level="ERROR",
                                )
                        else:
                            # Clean up raw image on failure
                            s3.delete_object(
                                Bucket=os.getenv("AWS_BUCKET_NAME"),
                                Key=raw_image_key,
                            )
                            self.message_user(
                                request,
                                "Failed to download image for processing. Please try again.",
                                level="ERROR",
                            )

                except Exception as e:
                    self.message_user(
                        request,
                        f"Error uploading avatar: {e!s}",
                        level="ERROR",
                    )

        # Handle avatar removal
        remove_avatar = form.cleaned_data.get("remove_avatar")
        if remove_avatar:
            try:
                from .models import Avatar

                avatar = Avatar.objects.filter(
                    bot=obj,
                    bot_conversation__isnull=True,
                ).first()

                if avatar and avatar.chatbot_avatar:
                    # Store filename before clearing
                    removed_filename = avatar.chatbot_avatar

                    # Delete the avatar file
                    import os

                    is_local = os.getenv("BACKEND_ENVIRONMENT") == "local"

                    if is_local:
                        # Delete local file
                        from pathlib import Path

                        from django.conf import settings

                        local_path = (
                            Path(settings.MEDIA_ROOT)
                            / "avatars"
                            / avatar.chatbot_avatar
                        )
                        if local_path.exists():
                            local_path.unlink()
                    else:
                        # Delete from S3
                        delete("avatar", avatar.chatbot_avatar)

                    # Clear the avatar record
                    avatar.chatbot_avatar = None
                    avatar.save()

                    # Set bot avatar type to 'none'
                    obj.avatar_type = "none"
                    obj.save()

                    self.message_user(
                        request,
                        f"Avatar removed successfully: {removed_filename}",
                        level="SUCCESS",
                    )
                else:
                    self.message_user(
                        request,
                        "No avatar found to remove.",
                        level="WARNING",
                    )
            except Exception as e:
                self.message_user(
                    request,
                    f"Error removing avatar: {e!s}",
                    level="ERROR",
                )

    def delete_model(self, request, obj):
        """Clean up avatar files when bot is deleted"""
        try:
            from .models import Avatar

            avatars = Avatar.objects.filter(bot=obj)
            for avatar in avatars:
                if avatar.chatbot_avatar:
                    delete("avatar", avatar.chatbot_avatar)
                if avatar.participant_avatar:
                    delete("avatar", avatar.participant_avatar)
        except Exception:
            pass  # Don't prevent deletion if cleanup fails

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Clean up avatar files when bots are bulk deleted"""
        try:
            from .models import Avatar

            for obj in queryset:
                avatars = Avatar.objects.filter(bot=obj)
                for avatar in avatars:
                    if avatar.chatbot_avatar:
                        delete("avatar", avatar.chatbot_avatar)
                    if avatar.participant_avatar:
                        delete("avatar", avatar.participant_avatar)
        except Exception:
            pass  # Don't prevent deletion if cleanup fails

        super().delete_queryset(request, queryset)


@admin.register(Avatar)
class AvatarAdmin(BaseAdmin):
    list_display = (
        "bot_name",
        "bot_conversation",
        "condition",
        "avatar_preview",
        "has_participant_avatar",
        "has_chatbot_avatar",
    )
    list_display_links = ("bot_name",)
    search_fields = ("bot__name", "bot_conversation")
    list_filter = ("condition", "bot__avatar_type")
    ordering = ("bot__name", "bot_conversation")
    readonly_fields = (
        "bot_name",
        "bot_conversation",
        "condition",
        "avatar_preview_field",
    )

    def bot_name(self, obj):
        return obj.bot.name if obj.bot else "No Bot"

    bot_name.short_description = "Bot"

    def avatar_preview(self, obj):
        """Display avatar preview in list view"""
        if obj.chatbot_avatar:
            try:
                # Check if we're in local development
                from django.conf import settings

                is_local = settings.BACKEND_ENVIRONMENT == "local"

                if is_local:
                    # For local development, serve from media directory
                    from pathlib import Path

                    local_path = (
                        Path(settings.MEDIA_ROOT) /
                        "avatars" / obj.chatbot_avatar
                    )
                    if local_path.exists():
                        image_url = f"/media/avatars/{obj.chatbot_avatar}"
                        return format_html(
                            '<img src="{}" alt="Chatbot Avatar" class="avatar-preview" title="{}" />',
                            image_url,
                            obj.chatbot_avatar,
                        )
                else:
                    # Production: Get presigned URL for display
                    image_url = get_presigned_url(
                        "avatar",
                        obj.chatbot_avatar,
                        expiration=3600,
                    )
                    if image_url:
                        return format_html(
                            '<img src="{}" alt="Chatbot Avatar" class="avatar-preview" title="{}" />',
                            image_url,
                            obj.chatbot_avatar,
                        )
            except Exception:
                pass
        return format_html('<span class="no-avatar">No chatbot avatar</span>')

    avatar_preview.short_description = "Chatbot Avatar"

    def avatar_preview_field(self, obj):
        """Display both avatars in detail view"""
        html_parts = []

        if obj.participant_avatar:
            try:
                participant_url = get_presigned_url(
                    "avatar",
                    obj.participant_avatar,
                    expiration=3600,
                )
                if participant_url:
                    html_parts.append(
                        f'<div class="avatar-detail-section"><strong>Participant Avatar:</strong><br>'
                        f'<img src="{participant_url}" alt="Participant Avatar" class="avatar-detail" /><br>'
                        f"<small>{obj.participant_avatar}</small></div>",
                    )
            except Exception:
                html_parts.append(
                    "<div class='avatar-detail-section'><strong>Participant Avatar:</strong> Error loading image</div>",
                )

        if obj.chatbot_avatar:
            try:
                # Check if we're in local development
                from django.conf import settings

                is_local = settings.BACKEND_ENVIRONMENT == "local"

                if is_local:
                    # For local development, serve from media directory
                    from pathlib import Path

                    local_path = (
                        Path(settings.MEDIA_ROOT) /
                        "avatars" / obj.chatbot_avatar
                    )
                    if local_path.exists():
                        chatbot_url = f"/media/avatars/{obj.chatbot_avatar}"
                        html_parts.append(
                            f'<div class="avatar-detail-section"><strong>Chatbot Avatar:</strong><br>'
                            f'<img src="{chatbot_url}" alt="Chatbot Avatar" class="avatar-detail" /><br>'
                            f"<small>{obj.chatbot_avatar}</small></div>",
                        )
                    else:
                        html_parts.append(
                            "<div class='avatar-detail-section'><strong>Chatbot Avatar:</strong> File not found</div>",
                        )
                else:
                    # Production: Get presigned URL for display
                    chatbot_url = get_presigned_url(
                        "avatar",
                        obj.chatbot_avatar,
                        expiration=3600,
                    )
                    if chatbot_url:
                        html_parts.append(
                            f'<div class="avatar-detail-section"><strong>Chatbot Avatar:</strong><br>'
                            f'<img src="{chatbot_url}" alt="Chatbot Avatar" class="avatar-detail" /><br>'
                            f"<small>{obj.chatbot_avatar}</small></div>",
                        )
                    else:
                        html_parts.append(
                            "<div class='avatar-detail-section'><strong>Chatbot Avatar:</strong> Error loading image</div>",
                        )
            except Exception:
                html_parts.append(
                    "<div class='avatar-detail-section'><strong>Chatbot Avatar:</strong> Error loading image</div>",
                )

        if not html_parts:
            return format_html('<span class="no-avatar">No avatars available</span>')

        return format_html("".join(html_parts))

    avatar_preview_field.short_description = "Avatar Images"

    def has_participant_avatar(self, obj):
        return bool(obj.participant_avatar)

    has_participant_avatar.boolean = True
    has_participant_avatar.short_description = "Has Participant Avatar"

    def has_chatbot_avatar(self, obj):
        return bool(obj.chatbot_avatar)

    has_chatbot_avatar.boolean = True
    has_chatbot_avatar.short_description = "Has Chatbot Avatar"

    def has_add_permission(self, request):
        # Avatars are created automatically, don't allow manual creation
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing but not editing
        return False

    fieldsets = (
        (
            "Bot Information",
            {
                "fields": ("bot_name", "bot_conversation", "condition"),
            },
        ),
        (
            "Avatar Images",
            {
                "fields": ("avatar_preview_field",),
                "description": "View avatar images stored in S3",
            },
        ),
    )

    actions = ["delete_avatars"]

    def delete_avatars(self, request, queryset):
        """Custom action to delete avatar files from S3"""
        deleted_count = 0
        errors = []

        # Collect all avatars to delete first
        avatars_to_delete = list(queryset)

        # Delete avatars and collect errors
        for avatar in avatars_to_delete:
            # Delete S3 files first
            if avatar.participant_avatar:
                try:
                    delete("avatar", avatar.participant_avatar)
                except Exception as e:
                    errors.append(
                        f"Avatar {avatar.id} participant file: {e!s}")

            if avatar.chatbot_avatar:
                try:
                    delete("avatar", avatar.chatbot_avatar)
                except Exception as e:
                    errors.append(f"Avatar {avatar.id} chatbot file: {e!s}")

            # Delete the avatar record
            try:
                avatar.delete()
                deleted_count += 1
            except Exception as e:
                errors.append(f"Avatar {avatar.id} record: {e!s}")

        # Report any errors
        for error in errors:
            self.message_user(
                request, f"Error deleting {error}", level="ERROR")

        self.message_user(
            request,
            f"Successfully deleted {deleted_count} avatar(s) and their files from S3.",
            level="SUCCESS",
        )

    delete_avatars.short_description = "Delete selected avatars and their files"


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
        (
            "Session Information",
            {
                "fields": ("conversation_id", "timestamp"),
            },
        ),
        (
            "Timing Data",
            {
                "fields": (
                    "total_time_on_page",
                    "total_time_away_from_page",
                    "keystroke_count",
                ),
            },
        ),
    )


@admin.register(ModerationSettings)
class ModerationSettingsAdmin(BaseAdmin):
    list_display = ("enabled", "updated_at")
    list_display_links = None
    list_editable = ("enabled",)

    def has_add_permission(self, request):
        return False  # Never allow manual creation

    def has_delete_permission(self, request, obj=None):
        return False  # Never allow deletion

    def changelist_view(self, request, extra_context=None):
        # Auto-create default record if none exists
        if not ModerationSettings.objects.exists():
            ModerationSettings.objects.create(enabled=True)
        return super().changelist_view(request, extra_context)
