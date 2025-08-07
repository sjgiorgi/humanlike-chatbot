from django.urls import path

from .services.avatar import AvatarAPIView, AvatarDetailAPIView
from .services.bots import BotDetailAPIView, ListBotsAPIView  # Import from bots.py
from .services.conversation import (
    InitializeConversationAPIView,  # Import from conversation.py
)
from .services.keystroke import update_keystrokes
from .services.upload import get_presigned_url
from .services.voicechat import get_realtime_session, upload_voice_utterance
from .views import ChatbotAPIView, health_check, test_upload

urlpatterns = [
    # 1) Health Check
    path("health/", health_check, name="health_check"),
    # 2) Test Upload
    path("test-upload/", test_upload, name="test_upload"),
    # 2) Initialize a Conversation
    path(
        "api/initialize_conversation/",
        InitializeConversationAPIView.as_view(),
        name="initialize_conversation",
    ),
    # 3) Chatbot Conversation Endpoint
    path("api/chatbot/", ChatbotAPIView.as_view(), name="chatbot_api"),
    # 4) Bots Collection (List and/or Create)
    path("api/bots/", ListBotsAPIView.as_view(), name="list_bots"),
    # 5) Bot Detail by Primary Key (Retrieve, Update, Delete)
    path("api/bots/<int:pk>/", BotDetailAPIView.as_view(), name="bot-detail"),
    # 6) update keystrokes
    path("api/update_keystrokes/", update_keystrokes, name="update_keystrokes"),
    # 7) get realtime sesion
    path("api/session/", get_realtime_session, name="get_realtime_session"),
    # 8) upload voice data
    path(
        "api/upload_voice_utterance/",
        upload_voice_utterance,
        name="upload_voice_utterance",
    ),
    # 9) Generate and Access Bot Avatar
    path("api/avatar/", AvatarAPIView.as_view(), name="avatar"),
    path(
        "api/avatar/<str:bot_name>/",
        AvatarDetailAPIView.as_view(),
        name="avatar-detail",
    ),
    path("api/avatar-upload/", get_presigned_url, name="avatar-upload"),
]
