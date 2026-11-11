import pytest
from django.utils import timezone

from apps.catalog.models import Option
from apps.practice.models import Attempt
from tests.helpers import V1, client_for

pytestmark = pytest.mark.django_db


def right(qid):
    return Option.objects.get(question_id=qid, is_correct=True).label


def wrong(qid):
    return Option.objects.filter(question_id=qid, is_correct=False).order_by("label").first().label


def run_attempt(api, n_right, n_wrong, exam="iba_mba_2016_dec", section_no=2, seconds=20):
    a = api.post(f"{V1}/attempts/", {"mode": "sectional", "exam": exam, "section_no": section_no}, format="json").data
    qs = a["questions"]
    for q in qs[:n_right]:
        api.post(f"{V1}/attempts/{a['id']}/answers/",
                 {"question": q["id"], "option": right(q["id"]), "time_spent": seconds}, format="json")
    for q in qs[n_right:n_right + n_wrong]:
        api.post(f"{V1}/attempts/{a['id']}/answers/",
                 {"question": q["id"], "option": wrong(q["id"]), "time_spent": seconds}, format="json")
    api.post(f"{V1}/attempts/{a['id']}/submit/")
    return a


def test_empty_overview_for_a_new_user():
    d = client_for("new@example.com").get(f"{V1}/analytics/overview/").data
    assert d["totals"] == {"attempts": 0, "answered": 0, "correct": 0, "accuracy": 0.0,
                           "avg_seconds_per_question": 0, "active_days": 0, "streak_days": 0}
    assert d["by_subject"] == [] and d["weakest"] == [] and d["trend"] == []


def test_overview_counts_only_answered_questions_of_finished_attempts():
    api = client_for("a@example.com")
    run_attempt(api, n_right=6, n_wrong=4, seconds=30)
    api.post(f"{V1}/attempts/", {"mode": "sectional", "exam": "iba_mba_2016_dec", "section_no": 2}, format="json")
    d = api.get(f"{V1}/analytics/overview/").data
    t = d["totals"]
    assert (t["attempts"], t["answered"], t["correct"]) == (1, 10, 6)  # the unfinished attempt is ignored
    assert t["accuracy"] == 0.6 and t["avg_seconds_per_question"] == 30
    assert t["active_days"] == 1 and t["streak_days"] == 1
    subj = {s["subject"]: s for s in d["by_subject"]}
    assert subj["mathematics"]["answered"] == 10 and subj["mathematics"]["accuracy"] == 0.6
    assert sum(x["answered"] for x in d["by_topic"]) == 10


def test_blank_answers_are_not_counted():
    api = client_for("b@example.com")
    run_attempt(api, n_right=2, n_wrong=0)
    assert api.get(f"{V1}/analytics/overview/").data["totals"]["answered"] == 2


def test_weakest_topics_need_enough_answers_and_are_sorted():
    api = client_for("c@example.com")
    run_attempt(api, n_right=0, n_wrong=30)  # every answer wrong
    d = api.get(f"{V1}/analytics/overview/").data
    assert d["weakest"] and all(w["answered"] >= d["min_answers_for_weak"] for w in d["weakest"])
    acc = [w["accuracy"] for w in d["weakest"]]
    assert acc == sorted(acc) and acc[0] == 0.0


def test_trend_is_oldest_first_with_score_percentages():
    api = client_for("d@example.com")
    first = run_attempt(api, n_right=5, n_wrong=0)
    run_attempt(api, n_right=0, n_wrong=5, section_no=1)
    d = api.get(f"{V1}/analytics/overview/").data
    assert [t["attempt_id"] for t in d["trend"]][0] == first["id"]
    assert d["trend"][0]["score_pct"] > d["trend"][1]["score_pct"]


def test_streak_requires_consecutive_days():
    api = client_for("e@example.com")
    a = run_attempt(api, 3, 0)
    b = run_attempt(api, 3, 0, section_no=1)
    Attempt.objects.filter(id=a["id"]).update(submitted_at=timezone.now() - timezone.timedelta(days=1))
    assert api.get(f"{V1}/analytics/overview/").data["totals"]["streak_days"] == 2
    Attempt.objects.filter(id=a["id"]).update(submitted_at=timezone.now() - timezone.timedelta(days=3))
    Attempt.objects.filter(id=b["id"]).update(submitted_at=timezone.now())
    assert api.get(f"{V1}/analytics/overview/").data["totals"]["streak_days"] == 1


def test_analytics_are_private_per_user():
    run_attempt(client_for("f@example.com"), 5, 0)
    assert client_for("g@example.com").get(f"{V1}/analytics/overview/").data["totals"]["answered"] == 0


def test_topic_frequency_covers_every_non_writing_question():
    d = client_for("h@example.com").get(f"{V1}/analytics/topic-frequency/").data
    assert d["years"][0] == 2015 and d["years"][-1] == 2025
    assert sum(t["total"] for t in d["topics"]) == 741 - 26
    assert all(sum(t["by_year"].values()) == t["total"] for t in d["topics"])
    assert [t["total"] for t in d["topics"]] == sorted((t["total"] for t in d["topics"]), reverse=True)


def test_analytics_require_login():
    from rest_framework.test import APIClient

    assert APIClient().get(f"{V1}/analytics/overview/").status_code == 401
