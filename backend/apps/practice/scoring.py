from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Attempt, AttemptQuestion

ONE = Decimal("1")


def finalize(attempt: Attempt, status: str = Attempt.Status.SUBMITTED) -> Attempt:
    """Score an attempt exactly once. Safe to call repeatedly: finished attempts are returned untouched."""
    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.is_finished:
            return attempt
        items = list(attempt.items.select_related("question").prefetch_related("question__options"))
        score = max_score = Decimal("0")
        correct = wrong = unanswered = 0
        for item in items:
            marks = item.question.marks or ONE
            max_score += marks
            if not item.selected_label:
                item.is_correct, item.marks_awarded = None, Decimal("0")
                unanswered += 1
            else:
                right = next((o.label for o in item.question.options.all() if o.is_correct), None)
                if item.selected_label == right:
                    item.is_correct, item.marks_awarded = True, marks
                    correct += 1
                else:
                    item.is_correct, item.marks_awarded = False, -attempt.negative_mark
                    wrong += 1
            score += item.marks_awarded
        AttemptQuestion.objects.bulk_update(items, ["is_correct", "marks_awarded"])
        attempt.score, attempt.max_score = score, max_score
        attempt.correct, attempt.wrong, attempt.unanswered = correct, wrong, unanswered
        attempt.status, attempt.submitted_at = status, timezone.now()
        attempt.save()
    return attempt


def finalize_if_expired(attempt: Attempt) -> Attempt:
    if not attempt.is_finished and attempt.deadline_at and timezone.now() >= attempt.deadline_at:
        return finalize(attempt, Attempt.Status.EXPIRED)
    return attempt


def breakdown(attempt: Attempt, key) -> list[dict]:
    """Aggregate a finished attempt's items. `key(item)` -> (id, label, extra_dict)."""
    rows: dict = defaultdict(lambda: {"correct": 0, "wrong": 0, "unanswered": 0, "score": Decimal("0"), "total": 0})
    meta = {}
    for item in attempt.items.all():
        k, label, extra = key(item)
        meta[k] = {"id": k, "label": label, **extra}
        r = rows[k]
        r["total"] += 1
        r["score"] += item.marks_awarded or 0
        if item.is_correct:
            r["correct"] += 1
        elif item.is_correct is False:
            r["wrong"] += 1
        else:
            r["unanswered"] += 1
    return [{**meta[k], **v, "score": float(v["score"]),
             "accuracy": round(v["correct"] / v["total"], 3) if v["total"] else 0} for k, v in rows.items()]
