"""Read-only statistics. Per-user numbers come only from that user's *finished* attempts; a question left blank
is not counted as an answer."""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Question
from apps.practice.models import Attempt, AttemptQuestion

MIN_FOR_WEAK = 3  # a topic needs this many answers before it can be called weak


def _rate(correct: int, answered: int) -> float:
    return round(correct / answered, 3) if answered else 0.0


def _streak(days: set) -> int:
    """Consecutive days with a finished attempt, ending today (or yesterday, so an evening streak isn't lost)."""
    today = timezone.localdate()
    cursor = today if today in days else today - timedelta(days=1)
    n = 0
    while cursor in days:
        n += 1
        cursor -= timedelta(days=1)
    return n


class OverviewView(APIView):
    def get(self, request):
        finished = Attempt.objects.filter(user=request.user).exclude(status=Attempt.Status.IN_PROGRESS)
        answered = AttemptQuestion.objects.filter(attempt__in=finished).exclude(selected_label="")
        ok = Q(is_correct=True)

        t = answered.aggregate(n=Count("id"), correct=Count("id", filter=ok), avg=Avg("time_spent"))
        days = {timezone.localtime(d).date() for d in finished.values_list("submitted_at", flat=True) if d}

        by_subject = [
            {"subject": r["question__section__subject__slug"], "answered": r["n"], "correct": r["c"],
             "accuracy": _rate(r["c"], r["n"])}
            for r in answered.values("question__section__subject__slug")
            .annotate(n=Count("id"), c=Count("id", filter=ok)).order_by("question__section__subject__slug")
        ]
        by_topic = [
            {"topic_id": r["question__topic_id"], "topic": r["question__topic__name"],
             "subject": r["question__topic__subject__slug"], "answered": r["n"], "correct": r["c"],
             "accuracy": _rate(r["c"], r["n"]), "avg_seconds": round(r["t"] or 0)}
            for r in answered.exclude(question__topic__isnull=True)
            .values("question__topic_id", "question__topic__name", "question__topic__subject__slug")
            .annotate(n=Count("id"), c=Count("id", filter=ok), t=Avg("time_spent")).order_by("question__topic__name")
        ]
        weakest = sorted((x for x in by_topic if x["answered"] >= MIN_FOR_WEAK), key=lambda x: x["accuracy"])[:5]
        trend = [
            {"attempt_id": a.id, "date": a.submitted_at, "mode": a.mode,
             "score_pct": round(float(a.score) / float(a.max_score) * 100, 1) if a.max_score else 0.0}
            for a in reversed(list(finished.order_by("-submitted_at")[:20]))
        ]
        return Response({
            "totals": {"attempts": finished.count(), "answered": t["n"], "correct": t["correct"],
                       "accuracy": _rate(t["correct"], t["n"]), "avg_seconds_per_question": round(t["avg"] or 0),
                       "active_days": len(days), "streak_days": _streak(days)},
            "by_subject": by_subject, "by_topic": by_topic, "weakest": weakest, "trend": trend,
            "min_answers_for_weak": MIN_FOR_WEAK,
        })


class TopicFrequencyView(APIView):
    """Which topics the real papers test, and how often per year (essays and arguments excluded)."""

    def get(self, request):
        rows = (Question.objects.exclude(type__in=["essay", "argument"]).exclude(topic__isnull=True)
                .values("topic_id", "topic__name", "topic__subject__slug", "section__exam__year")
                .annotate(n=Count("id")))
        topics: dict = {}
        years = set()
        for r in rows:
            t = topics.setdefault(r["topic_id"], {"id": r["topic_id"], "name": r["topic__name"],
                                                  "subject": r["topic__subject__slug"], "total": 0,
                                                  "by_year": defaultdict(int)})
            t["total"] += r["n"]
            t["by_year"][r["section__exam__year"]] += r["n"]
            years.add(r["section__exam__year"])
        out = sorted(topics.values(), key=lambda t: -t["total"])
        for t in out:
            t["by_year"] = dict(t["by_year"])
        return Response({"years": sorted(years), "topics": out})
