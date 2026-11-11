from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.catalog.models import Question, Solution

from .serializers import AnswerVerifySerializer, ReviewEditSerializer, ReviewQuestionSerializer, log_changes


class IsReviewer(permissions.BasePermission):
    message = "Reviewer access required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in (User.Role.REVIEWER, User.Role.ADMIN))


class ReviewQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReviewQuestionSerializer
    permission_classes = [IsReviewer]

    def get_queryset(self):
        qs = (Question.objects.select_related("section__exam", "section__subject", "topic", "group", "solution")
              .prefetch_related("options").order_by("section__exam__year", "section__exam__month",
                                                    "section__section_no", "order"))
        p = self.request.query_params
        bn = p.get("bn")
        if bn == "missing":  # no Bangla at all
            qs = qs.filter(stem_bn="").exclude(type__in=["essay", "argument"])
        elif bn in ("draft", "reviewed"):
            qs = qs.filter(bn_status=bn).exclude(stem_bn="")
        if p.get("exam"):
            qs = qs.filter(section__exam__slug=p["exam"])
        if p.get("subject"):
            qs = qs.filter(section__subject__slug=p["subject"])
        if p.get("answer_status"):
            qs = qs.filter(answer_status=p["answer_status"])
        if p.get("flagged") == "1":
            qs = qs.filter(~Q(review_note="") | ~Q(source_defect=""))
        if p.get("search"):
            qs = qs.filter(Q(stem__icontains=p["search"]) | Q(stem_bn__icontains=p["search"]))
        return qs

    @action(detail=False, methods=["get"])
    def summary(self, request):
        base = Question.objects.exclude(type__in=["essay", "argument"])
        has_bn = base.exclude(stem_bn="")
        return Response({
            "bangla": {
                "draft": has_bn.filter(bn_status="draft").count(),
                "reviewed": has_bn.filter(bn_status="reviewed").count(),
                "missing": base.filter(stem_bn="").count(),
            },
            "answers": dict(Question.objects.values_list("answer_status").annotate(c=Count("id"))),
            "flagged": Question.objects.filter(~Q(review_note="") | ~Q(source_defect="")).count(),
        })

    def partial_update(self, request, pk=None):
        q = get_object_or_404(self.get_queryset(), pk=pk)
        ser = ReviewEditSerializer(data=request.data, context={"question": q})
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        changes: dict[str, tuple[str, str]] = {}
        with transaction.atomic():
            if "stem_bn" in d:
                changes["stem_bn"] = (q.stem_bn, d["stem_bn"])
                q.stem_bn = d["stem_bn"]
            if "bn_status" in d:
                changes["bn_status"] = (q.bn_status, d["bn_status"])
                q.bn_status = d["bn_status"]
            elif "stem_bn" in d and q.bn_status == "reviewed" and changes["stem_bn"][0] != d["stem_bn"]:
                # An edited translation is no longer reviewed.
                changes["bn_status"] = ("reviewed", "draft")
                q.bn_status = "draft"
            q.save()
            for o in q.options.all():
                if o.label in d.get("options_bn", {}):
                    changes[f"option_bn:{o.label}"] = (o.text_bn, d["options_bn"][o.label])
                    o.text_bn = d["options_bn"][o.label]
                    o.save(update_fields=["text_bn", "updated_at"])
            if "solution_body_bn" in d:
                sol, _ = Solution.objects.get_or_create(question=q)
                changes["solution_body_bn"] = (sol.body_bn, d["solution_body_bn"])
                sol.body_bn = d["solution_body_bn"]
                sol.save(update_fields=["body_bn", "updated_at"])
            log_changes(request.user, q, changes)
        q = self.get_queryset().get(pk=q.pk)
        return Response(ReviewQuestionSerializer(q).data)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        """Record a reviewer's verdict on the answer key (status and, optionally, the correct option)."""
        q = get_object_or_404(self.get_queryset(), pk=pk)
        ser = AnswerVerifySerializer(data=request.data, context={"question": q})
        ser.is_valid(raise_exception=True)
        status, label = ser.validated_data["answer_status"], ser.validated_data["_label"]
        old_label = next((o.label for o in q.options.all() if o.is_correct), "")
        with transaction.atomic():
            for o in q.options.all():
                want = o.label == label
                if o.is_correct != want:
                    o.is_correct = want
                    o.save(update_fields=["is_correct", "updated_at"])
            changes = {"answer_status": (q.answer_status, status), "correct_option": (old_label, label or "")}
            if (label or "") != old_label and old_label:
                q.answer_prev = old_label
            q.answer_status, q.answer_source = status, "reviewer"
            q.save()
            log_changes(request.user, q, changes)
        return Response(ReviewQuestionSerializer(self.get_queryset().get(pk=q.pk)).data)
