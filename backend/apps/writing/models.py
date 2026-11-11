from django.conf import settings
from django.db import models

from apps.catalog.models import Question, UUIDModel


class WritingSubmission(UUIDModel):
    class Status(models.TextChoices):
        DONE = "done"
        FAILED = "failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="writings")
    prompt = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="submissions")
    body = models.TextField()
    word_count = models.PositiveIntegerField()
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.FAILED)
    feedback = models.JSONField(null=True, blank=True)
    model = models.CharField(max_length=60, blank=True)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
