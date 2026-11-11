from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Question
from apps.catalog.serializers import ExamSerializer, QuestionSerializer, reveal

from .models import Attempt, Bookmark


class AttemptCreateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=Attempt.Mode.choices)
    exam = serializers.SlugField(required=False)
    section_no = serializers.IntegerField(required=False, min_value=1)
    topics = serializers.ListField(child=serializers.UUIDField(), required=False)
    subject = serializers.SlugField(required=False)
    type = serializers.ChoiceField(choices=Question.Type.choices, required=False)
    count = serializers.IntegerField(required=False, min_value=1, max_value=100)
    timed = serializers.BooleanField(required=False)


class AnswerSerializer(serializers.Serializer):
    question = serializers.UUIDField()
    option = serializers.CharField(max_length=2, allow_blank=True, required=False)  # "" clears the answer
    flagged = serializers.BooleanField(required=False)
    time_spent = serializers.IntegerField(required=False, min_value=0, max_value=86400)  # seconds added


def response_of(item) -> dict:
    return {"selected": item.selected_label or None, "flagged": item.flagged, "time_spent": item.time_spent}


def attempt_summary(attempt: Attempt) -> dict:
    return {
        "id": attempt.id, "mode": attempt.mode, "status": attempt.status, "server_now": timezone.now(),
        "exam": ExamSerializer(attempt.exam).data if attempt.exam_id else None,
        "started_at": attempt.started_at, "deadline_at": attempt.deadline_at, "submitted_at": attempt.submitted_at,
        "time_limit_seconds": attempt.time_limit_seconds, "negative_mark": float(attempt.negative_mark),
        "score": None if attempt.score is None else float(attempt.score),
        "max_score": None if attempt.max_score is None else float(attempt.max_score),
        "correct": attempt.correct, "wrong": attempt.wrong, "unanswered": attempt.unanswered,
    }


def attempt_detail(attempt: Attempt, items, request) -> dict:
    """In-progress view: questions and the user's own responses, never the answers."""
    ctx = {"request": request}
    return {
        **attempt_summary(attempt),
        "questions": [{**QuestionSerializer(i.question, context=ctx).data, "response": response_of(i)} for i in items],
    }


def attempt_result(attempt: Attempt, items, request) -> dict:
    ctx = {"request": request}
    review = []
    for i in items:
        review.append({
            **QuestionSerializer(i.question, context=ctx).data,
            "response": response_of(i),
            "is_correct": i.is_correct,
            "marks_awarded": None if i.marks_awarded is None else float(i.marks_awarded),
            **reveal(i.question),
        })
    return {**attempt_summary(attempt), "review": review}


class BookmarkSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(), source="question", write_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "created_at", "question", "question_id"]
        read_only_fields = ["id", "created_at"]
