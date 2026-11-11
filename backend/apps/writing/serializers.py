import re

from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Question

from .models import WritingSubmission

_PREFIX = re.compile(r"^\s*(?:\d+|[A-Z])\.\s+")


def words(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


class PromptSerializer(serializers.ModelSerializer):
    exam = serializers.CharField(source="section.exam.slug")
    session = serializers.CharField(source="section.exam.session")
    year = serializers.IntegerField(source="section.exam.year")
    instruction = serializers.CharField(source="group.instruction", default="")
    stem = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "exam", "session", "year", "number", "type", "stem", "instruction", "marks"]

    def get_stem(self, q):
        return _PREFIX.sub("", q.stem)


class SubmissionSerializer(serializers.ModelSerializer):
    prompt = PromptSerializer(read_only=True)

    class Meta:
        model = WritingSubmission
        fields = ["id", "prompt", "body", "word_count", "status", "feedback", "error", "created_at"]


class SubmissionCreateSerializer(serializers.Serializer):
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.filter(type__in=["essay", "argument"]), source="question")
    body = serializers.CharField(trim_whitespace=True)

    def validate_body(self, value):
        n = words(value)
        if n < settings.WRITING_MIN_WORDS:
            raise serializers.ValidationError(f"Write at least {settings.WRITING_MIN_WORDS} words (you have {n}).")
        if n > settings.WRITING_MAX_WORDS:
            raise serializers.ValidationError(f"Keep it under {settings.WRITING_MAX_WORDS} words (you have {n}).")
        return value
