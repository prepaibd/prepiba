from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import scoring, selection
from .models import Attempt, AttemptQuestion, Bookmark
from .serializers import (
    AnswerSerializer,
    AttemptCreateSerializer,
    BookmarkSerializer,
    attempt_detail,
    attempt_result,
    attempt_summary,
)


class AttemptViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = AttemptCreateSerializer
    filterset_fields = ["status", "mode"]

    def get_queryset(self):
        return Attempt.objects.filter(user=self.request.user).select_related("exam")

    def get_object(self):
        attempt = super().get_object()
        return scoring.finalize_if_expired(attempt)

    def _items(self, attempt):
        return list(attempt.items.select_related(
            "question__section__exam", "question__section__subject", "question__topic__subject", "question__group",
        ).prefetch_related("question__options", "question__figures", "question__solution__formulas",
                           "question__solution__rules"))

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response([attempt_summary(a) for a in page])

    def create(self, request, *args, **kwargs):
        ser = AttemptCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            plan = selection.build_plan(ser.validated_data)
        except DjangoValidationError as e:
            raise ValidationError({"detail": e.messages}) from e
        now = timezone.now()
        with transaction.atomic():
            attempt = Attempt.objects.create(
                user=request.user, mode=ser.validated_data["mode"], exam=plan.exam, config=plan.config,
                time_limit_seconds=plan.time_limit_seconds, negative_mark=plan.negative_mark,
                deadline_at=now + timedelta(seconds=plan.time_limit_seconds) if plan.time_limit_seconds else None,
            )
            AttemptQuestion.objects.bulk_create(
                [AttemptQuestion(attempt=attempt, question=q, order=i) for i, q in enumerate(plan.questions, 1)])
        return Response(attempt_detail(attempt, self._items(attempt), request), status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        attempt = self.get_object()
        return Response(attempt_detail(attempt, self._items(attempt), request))

    @action(detail=True, methods=["post"])
    def answers(self, request, pk=None):
        attempt = self.get_object()
        if attempt.is_finished:
            return Response({"detail": "This attempt is finished.", "status": attempt.status},
                            status=status.HTTP_409_CONFLICT)
        ser = AnswerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        item = get_object_or_404(attempt.items.select_related("question").prefetch_related("question__options"),
                                 question_id=d["question"])
        update = []
        if "option" in d:
            label = d["option"].upper()
            if label and label not in {o.label for o in item.question.options.all()}:
                raise ValidationError({"option": "Not an option of this question"})
            item.selected_label = label
            item.answered_at = timezone.now() if label else None
            update += ["selected_label", "answered_at"]
        if "flagged" in d:
            item.flagged = d["flagged"]
            update.append("flagged")
        if d.get("time_spent"):
            item.time_spent += d["time_spent"]
            update.append("time_spent")
        if update:
            item.save(update_fields=update + ["updated_at"])
        return Response({"saved": True, "server_now": timezone.now(), "response": {
            "selected": item.selected_label or None, "flagged": item.flagged, "time_spent": item.time_spent}})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        attempt = scoring.finalize(self.get_object())
        return Response(attempt_summary(attempt))

    @action(detail=True, methods=["get"])
    def result(self, request, pk=None):
        attempt = self.get_object()
        if not attempt.is_finished:
            return Response({"detail": "Submit the attempt to see results."}, status=status.HTTP_409_CONFLICT)
        items = self._items(attempt)
        data = attempt_result(attempt, items, request)
        data["by_section"] = scoring.breakdown(
            attempt, lambda i: (i.question.section.section_no, i.question.section.subject.slug,
                                {"subject": i.question.section.subject.slug,
                                 "section_no": i.question.section.section_no}))
        data["by_topic"] = scoring.breakdown(
            attempt, lambda i: (str(i.question.topic_id), i.question.topic.name if i.question.topic else "Untagged",
                                {"subject": i.question.topic.subject.slug if i.question.topic else None}))
        return Response(data)


class BookmarkViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = BookmarkSerializer
    lookup_field = "question_id"

    def get_queryset(self):
        return (Bookmark.objects.filter(user=self.request.user)
                .select_related("question__section__exam", "question__section__subject", "question__topic__subject",
                                "question__group")
                .prefetch_related("question__options", "question__figures"))

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                ser.save(user=request.user)
        except IntegrityError:  # already bookmarked: idempotent
            pass
        question = ser.validated_data["question"]
        obj = Bookmark.objects.get(user=request.user, question=question)
        data = BookmarkSerializer(self.get_queryset().get(pk=obj.pk), context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

