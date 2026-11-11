from django.conf import settings
from django.db import models

from apps.catalog.models import Exam, Question, UUIDModel


class Attempt(UUIDModel):
    class Mode(models.TextChoices):
        MOCK_FULL = "mock_full"  # whole paper, timed
        PAST_PAPER = "past_paper"  # whole paper, untimed unless asked
        SECTIONAL = "sectional"  # one section of a paper
        TOPIC = "topic"  # random questions from chosen topics
        CUSTOM = "custom"  # random questions by subject / type

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        SUBMITTED = "submitted"
        EXPIRED = "expired"  # auto-submitted after the deadline

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    mode = models.CharField(max_length=12, choices=Mode.choices)
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True, related_name="attempts")
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    negative_mark = models.DecimalField(max_digits=4, decimal_places=2, default=0)  # snapshot at start
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    correct = models.PositiveSmallIntegerField(null=True, blank=True)
    wrong = models.PositiveSmallIntegerField(null=True, blank=True)
    unanswered = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "status"])]

    @property
    def is_finished(self):
        return self.status != self.Status.IN_PROGRESS


class AttemptQuestion(UUIDModel):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempt_items")
    order = models.PositiveSmallIntegerField()
    selected_label = models.CharField(max_length=2, blank=True)
    flagged = models.BooleanField(default=False)
    time_spent = models.PositiveIntegerField(default=0)  # seconds
    answered_at = models.DateTimeField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)  # set when finalised
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="uniq_attempt_question"),
            models.UniqueConstraint(fields=["attempt", "order"], name="uniq_attempt_order"),
        ]


class Bookmark(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="bookmarks")

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "question"], name="uniq_bookmark")]
