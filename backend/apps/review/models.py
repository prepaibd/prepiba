from django.conf import settings
from django.db import models

from apps.catalog.models import Question, UUIDModel


class ReviewLog(UUIDModel):
    """Who changed which reviewable field of a question, from what, to what."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="review_logs")
    field = models.CharField(max_length=60)  # e.g. "stem_bn", "option_bn:B", "solution_body_bn", "bn_status"
    old = models.TextField(blank=True)
    new = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["question", "-created_at"])]
