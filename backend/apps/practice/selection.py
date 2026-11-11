"""Choosing the questions for a new attempt and the attempt's rules (time, negative marking)."""
import math
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.catalog.models import Exam, Topic
from apps.catalog.views import question_queryset, scorable_filter

from .models import Attempt

DEFAULT_COUNT, MAX_COUNT = 20, 100


@dataclass
class Plan:
    exam: Exam | None
    questions: list
    time_limit_seconds: int | None
    negative_mark: float
    config: dict


def build_plan(params: dict) -> Plan:
    mode = params["mode"]
    qs = question_queryset().filter(scorable_filter())
    exam = None
    config = {k: params[k] for k in ("subject", "type", "section_no", "count") if params.get(k)}
    if params.get("topics"):
        config["topics"] = [str(t) for t in params["topics"]]

    if mode in (Attempt.Mode.MOCK_FULL, Attempt.Mode.PAST_PAPER, Attempt.Mode.SECTIONAL):
        exam = get_object_or_404(Exam, slug=params.get("exam"))
        qs = qs.filter(section__exam=exam)
        if mode == Attempt.Mode.SECTIONAL:
            if not params.get("section_no"):
                raise ValidationError("section_no is required for a sectional attempt")
            qs = qs.filter(section__section_no=params["section_no"])
        questions = list(qs.order_by("section__section_no", "order"))
    else:
        if mode == Attempt.Mode.TOPIC:
            ids = params.get("topics") or []
            if not ids:
                raise ValidationError("topics is required for a topic attempt")
            qs = qs.filter(topic__in=Topic.objects.filter(id__in=ids))
        if params.get("subject"):
            qs = qs.filter(section__subject__slug=params["subject"])
        if params.get("type"):
            qs = qs.filter(type=params["type"])
        count = min(int(params.get("count") or DEFAULT_COUNT), MAX_COUNT)
        questions = list(qs.order_by("?")[:count])

    if not questions:
        raise ValidationError("No scorable questions match this selection")

    timed = params.get("timed")
    if timed is None:
        timed = mode in (Attempt.Mode.MOCK_FULL, Attempt.Mode.SECTIONAL)
    limit = None
    if timed:
        if mode == Attempt.Mode.MOCK_FULL:
            limit = (exam.duration_minutes or settings.DEFAULT_DURATION_MINUTES) * 60
        else:
            limit = math.ceil(len(questions) * settings.SECONDS_PER_QUESTION)

    negative = exam.negative_mark if exam and exam.negative_mark is not None else settings.DEFAULT_NEGATIVE_MARK
    return Plan(exam, questions, limit, float(negative), config)
