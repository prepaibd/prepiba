from django.conf import settings
from django.db import models

from apps.catalog.models import UUIDModel


class AIUsageLog(UUIDModel):
    """One row per AI call. Only status=ok rows count towards a user's daily allowance."""

    class Kind(models.TextChoices):
        CHAT = "chat"
        WRITING = "writing"

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_usage")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.OK)
    model = models.CharField(max_length=60, blank=True)
    prompt_chars = models.PositiveIntegerField(default=0)
    output_chars = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "kind", "created_at"])]
