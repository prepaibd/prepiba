from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Question

from .models import ChatMessage, ChatSession


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]


class SessionSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ["id", "title", "question", "created_at", "updated_at"]

    def get_question(self, s):
        q = s.question
        if not q:
            return None
        return {"id": q.id, "exam": q.section.exam.session, "number": q.number, "stem": q.stem[:300]}


class SessionDetailSerializer(SessionSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(SessionSerializer.Meta):
        fields = SessionSerializer.Meta.fields + ["messages"]


class SessionCreateSerializer(serializers.Serializer):
    question_id = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all(), required=False, allow_null=True)


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(trim_whitespace=True, max_length=settings.CHAT_MAX_MESSAGE_CHARS)
