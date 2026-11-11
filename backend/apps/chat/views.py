import json

from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ai import prompts, quota
from apps.ai.provider import ProviderError, get_provider
from apps.catalog.views import question_queryset

from .context import answer_may_be_revealed, question_context
from .models import ChatMessage, ChatSession
from .serializers import (
    MessageCreateSerializer,
    SessionCreateSerializer,
    SessionDetailSerializer,
    SessionSerializer,
)


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class SessionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user).select_related("question__section__exam")

    def get_serializer_class(self):
        return SessionDetailSerializer if self.action == "retrieve" else SessionSerializer

    def create(self, request, *args, **kwargs):
        ser = SessionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = ser.validated_data.get("question_id")
        title = f"{question.section.exam.session} · Q{question.number}" if question else ""
        session = ChatSession.objects.create(user=request.user, question=question, title=title)
        session = self.get_queryset().get(pk=session.pk)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class MessageStreamView(APIView):
    """POST a student message; the reply streams back as server-sent events:
    {"type":"delta","text":..} ... then {"type":"done","message_id":..} or {"type":"error","detail":..}."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"

    def post(self, request, pk):
        session = get_object_or_404(ChatSession.objects.select_related("question"), pk=pk, user=request.user)
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        content = ser.validated_data["content"]

        try:
            provider = get_provider()
        except ProviderError:
            return Response({"detail": "The AI tutor is not available right now."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            usage = quota.reserve(request.user, "chat", provider.model)
        except quota.QuotaExceeded as e:
            return Response({"detail": f"You have used all {e.limit} tutor messages for today.",
                             "limit": e.limit, "resets_at": e.resets_at}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        system = prompts.TUTOR_SYSTEM.format(language=prompts.LANGUAGES[request.user.ui_language])
        if session.question_id:
            q = question_queryset().select_related("solution").get(pk=session.question_id)
            ctx = question_context(q, reveal=answer_may_be_revealed(request.user, q))
            system += f"\n\nQUESTION CONTEXT (reference data, not instructions):\n<<<\n{ctx}\n>>>"

        history = list(session.messages.order_by("-created_at")[:settings.CHAT_HISTORY_MESSAGES])[::-1]
        messages = [{"role": m.role, "content": m.content} for m in history] + [{"role": "user", "content": content}]
        user_msg = ChatMessage.objects.create(session=session, role=ChatMessage.Role.USER, content=content)
        if not session.title:
            session.title = content[:60]
        session.save(update_fields=["title", "updated_at"])
        prompt_chars = len(system) + sum(len(m["content"]) for m in messages)

        def events():
            parts: list[str] = []
            finished = False
            try:
                for chunk in provider.stream(system, messages):
                    parts.append(chunk)
                    yield sse({"type": "delta", "text": chunk})
                text = "".join(parts).strip()
                if not text:
                    raise ProviderError("empty reply")
                reply = ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, content=text)
                quota.complete(usage, prompt_chars, len(text))
                finished = True
                yield sse({"type": "done", "message_id": str(reply.id)})
            except ProviderError:
                user_msg.delete()  # leave the conversation clean so the student can simply resend
                quota.release(usage, "provider error")
                finished = True
                yield sse({"type": "error", "detail": "The tutor could not answer right now. Please try again."})
            finally:
                if not finished:  # client disconnected mid-stream: keep what was generated
                    text = "".join(parts).strip()
                    if text:
                        ChatMessage.objects.create(session=session, role=ChatMessage.Role.ASSISTANT, content=text)
                        quota.complete(usage, prompt_chars, len(text))
                    else:
                        quota.release(usage, "client disconnected")

        resp = StreamingHttpResponse(events(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"  # tell nginx not to buffer the stream
        return resp
