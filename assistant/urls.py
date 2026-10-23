"""URL routes for the SmartMeds assistant."""

from django.urls import path

from .views import AssistantChatView

app_name = "assistant"

urlpatterns = [
    path("chat/", AssistantChatView.as_view(), name="chat"),
]
