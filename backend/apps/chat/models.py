from django.conf import settings
from django.db import models

from apps.catalog.models import Question, UUIDModel


class ChatSession(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_sessions")
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    title = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-updated_at"]


class ChatMessage(UUIDModel):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()

    class Meta:
        ordering = ["created_at"]
