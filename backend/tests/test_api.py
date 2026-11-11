from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Option, Question, Topic
from apps.practice.models import Attempt

pytestmark = pytest.mark.django_db
V1 = "/api/v1"


def client_for(email="student@example.com"):
    c = APIClient()
    r = c.post(f"{V1}/auth/dev-login/", {"email": email}, format="json")
    assert r.status_code == 200, r.content
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return c


@pytest.fixture
def api():
    return client_for()


def correct_label(question_id):
    return Option.objects.get(question_id=question_id, is_correct=True).label


def wrong_label(question_id):
    return Option.objects.filter(question_id=question_id, is_correct=False).order_by("label").first().label


# ---- auth -------------------------------------------------------------------------------------------------

def test_anonymous_requests_are_rejected():
    assert APIClient().get(f"{V1}/exams/").status_code == 401


def test_google_login_creates_user_and_returns_tokens():
    claims = {"sub": "g-123", "email": "New@Example.com", "email_verified": True, "name": "New", "picture": "http://p"}
    with mock.patch("apps.accounts.views.verify_google_token", return_value=claims):
        r = APIClient().post(f"{V1}/auth/google/", {"id_token": "x"}, format="json")
    assert r.status_code == 200
    assert r.data["user"]["email"] == "new@example.com"
    assert User.objects.get(google_sub="g-123").name == "New"
    assert r.data["access"] and r.data["refresh"]


def test_google_login_rejects_bad_or_unverified_token():
    c = APIClient()
    with mock.patch("apps.accounts.views.verify_google_token", side_effect=ValueError("bad")):
        assert c.post(f"{V1}/auth/google/", {"id_token": "x"}, format="json").status_code == 401
    with mock.patch("apps.accounts.views.verify_google_token",
                    return_value={"sub": "1", "email": "a@b.com", "email_verified": False}):
        assert c.post(f"{V1}/auth/google/", {"id_token": "x"}, format="json").status_code == 401


def test_dev_login_is_404_when_disabled(settings):
    settings.DEV_LOGIN_ENABLED = False
    assert APIClient().post(f"{V1}/auth/dev-login/", {"email": "a@b.com"}, format="json").status_code == 404


def test_me_updates_language_but_not_role(api):
    r = api.patch(f"{V1}/auth/me/", {"ui_language": "bn", "role": "admin"}, format="json")
    assert r.status_code == 200 and r.data["ui_language"] == "bn" and r.data["role"] == "student"


# ---- catalog ----------------------------------------------------------------------------------------------

def test_exam_list_and_detail(api):
    exams = api.get(f"{V1}/exams/").data
    assert len(exams) == 14
    detail = api.get(f"{V1}/exams/iba_mba_2016_dec/").data
    assert detail["completeness"] == "full"
    assert [s["subject"] for s in detail["sections"]] == ["language", "mathematics", "analytical", "writing"]
    assert sum(s["question_count"] for s in detail["sections"]) == 77
    assert detail["scorable_count"] == sum(s["scorable_count"] for s in detail["sections"])


def test_question_payloads_never_leak_answers(api):
    r = api.get(f"{V1}/questions/", {"exam": "iba_mba_2016_dec", "section_no": 1})
    assert r.status_code == 200 and r.data["count"] == 30
    for q in r.data["results"]:
        assert "answer_text" not in q and "correct_label" not in q
        assert all("is_correct" not in o for o in q["options"])


def test_solution_endpoint_reveals_answer(api):
    q = Question.objects.filter(answer_status="verified", type="problem_solving").first()
    r = api.get(f"{V1}/questions/{q.id}/solution/")
    assert r.data["correct_label"] == correct_label(q.id)
    assert r.data["solution"]["body_en"]


def test_question_filters(api):
    r = api.get(f"{V1}/questions/", {"type": "data_sufficiency", "page_size": 5})
    assert r.data["count"] == 39
    topic = Topic.objects.filter(questions__isnull=False).first()
    assert api.get(f"{V1}/questions/", {"topic": str(topic.id)}).data["count"] >= 1


def test_question_search_matches_stem_and_options(api):
    q = Question.objects.filter(options__isnull=False).first()
    word = max(q.stem.split(), key=len)
    r = api.get(f"{V1}/questions/", {"search": word, "page_size": 200})
    assert str(q.id) in [x["id"] for x in r.data["results"]]
    assert api.get(f"{V1}/questions/", {"search": "zzzqqqxxx"}).data["count"] == 0


def test_figures_have_absolute_urls(api):
    q = Question.objects.filter(figures__isnull=False).first()
    fig = api.get(f"{V1}/questions/{q.id}/").data["figures"][0]
    assert fig["url"].startswith("http") and "/media/figures/" in fig["url"]


def test_learning_content_endpoints(api):
    assert len(api.get(f"{V1}/formulas/").data) == 22
    assert len(api.get(f"{V1}/rules/").data) == 26
    assert len(api.get(f"{V1}/subjects/").data) == 4


# ---- attempts: the phase gate -----------------------------------------------------------------------------

def test_full_2016_dec_mock_end_to_end(api):
    r = api.post(f"{V1}/attempts/", {"mode": "mock_full", "exam": "iba_mba_2016_dec"}, format="json")
    assert r.status_code == 201, r.content
    attempt_id, questions = r.data["id"], r.data["questions"]
    assert r.data["deadline_at"] and r.data["time_limit_seconds"] == 90 * 60  # fallback duration
    assert r.data["negative_mark"] == 0.25
    assert 60 < len(questions) <= 75  # scorable MCQs of the 77-question paper
    assert all(q["scorable"] and q["response"]["selected"] is None for q in questions)
    assert not any("is_correct" in o for q in questions for o in q["options"])

    # answer: first 40 right, next 15 wrong, flag one, leave the rest blank
    right, wrong = questions[:40], questions[40:55]
    for q in right:
        assert api.post(f"{V1}/attempts/{attempt_id}/answers/",
                        {"question": q["id"], "option": correct_label(q["id"]), "time_spent": 30},
                        format="json").data["saved"]
    for q in wrong:
        api.post(f"{V1}/attempts/{attempt_id}/answers/",
                 {"question": q["id"], "option": wrong_label(q["id"])}, format="json")
    api.post(f"{V1}/attempts/{attempt_id}/answers/", {"question": questions[60]["id"], "flagged": True}, format="json")

    # progress survives a reload and still hides answers
    reload = api.get(f"{V1}/attempts/{attempt_id}/").data
    assert reload["questions"][0]["response"] == {"selected": correct_label(questions[0]["id"]),
                                                  "flagged": False, "time_spent": 30}
    assert reload["questions"][60]["response"]["flagged"] is True
    assert api.get(f"{V1}/attempts/{attempt_id}/result/").status_code == 409  # not submitted yet

    summary = api.post(f"{V1}/attempts/{attempt_id}/submit/").data
    n = len(questions)
    assert summary["status"] == "submitted"
    assert (summary["correct"], summary["wrong"], summary["unanswered"]) == (40, 15, n - 55)
    assert summary["max_score"] == n  # 1 mark each
    assert summary["score"] == pytest.approx(40 - 15 * 0.25)

    # submitting again is idempotent; answering afterwards is refused
    again = api.post(f"{V1}/attempts/{attempt_id}/submit/").data
    assert again["score"] == summary["score"]
    late = api.post(f"{V1}/attempts/{attempt_id}/answers/",
                    {"question": questions[70]["id"], "option": "A"}, format="json")
    assert late.status_code == 409

    result = api.get(f"{V1}/attempts/{attempt_id}/result/").data
    assert len(result["review"]) == n
    first = result["review"][0]
    assert first["correct_label"] == first["response"]["selected"] and first["is_correct"] is True
    assert first["solution"]["body_en"]
    assert sum(s["correct"] for s in result["by_section"]) == 40
    assert sum(s["total"] for s in result["by_topic"]) == n
    assert sum(s["score"] for s in result["by_section"]) == pytest.approx(summary["score"])


def test_answer_validation(api):
    a = api.post(f"{V1}/attempts/", {"mode": "sectional", "exam": "iba_mba_2016_dec", "section_no": 2},
                 format="json").data
    qid = a["questions"][0]["id"]
    assert api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": qid, "option": "Z"},
                    format="json").status_code == 400
    other = Question.objects.exclude(section__exam__slug="iba_mba_2016_dec").first()
    assert api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": str(other.id), "option": "A"},
                    format="json").status_code == 404
    # clearing an answer
    api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": qid, "option": "A"}, format="json")
    cleared = api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": qid, "option": ""}, format="json")
    assert cleared.data["response"]["selected"] is None


def test_attempts_are_private_to_their_owner(api):
    a = api.post(f"{V1}/attempts/", {"mode": "sectional", "exam": "iba_mba_2016_dec", "section_no": 2},
                 format="json").data
    other = client_for("other@example.com")
    assert other.get(f"{V1}/attempts/{a['id']}/").status_code == 404
    assert other.get(f"{V1}/attempts/").data["count"] == 0
    assert api.get(f"{V1}/attempts/").data["count"] == 1


def test_expired_attempt_is_auto_submitted_and_scored(api):
    a = api.post(f"{V1}/attempts/", {"mode": "mock_full", "exam": "iba_mba_2016_dec"}, format="json").data
    q = a["questions"][0]
    api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": q["id"], "option": correct_label(q["id"])},
             format="json")
    Attempt.objects.filter(id=a["id"]).update(deadline_at=timezone.now() - timedelta(seconds=1))
    late = api.post(f"{V1}/attempts/{a['id']}/answers/", {"question": q["id"], "option": "A"}, format="json")
    assert late.status_code == 409 and late.data["status"] == "expired"
    done = Attempt.objects.get(id=a["id"])
    assert done.status == "expired" and done.correct == 1 and done.score == Decimal("1.00")


def test_management_command_submits_expired_attempts(api):
    a = api.post(f"{V1}/attempts/", {"mode": "mock_full", "exam": "iba_mba_2016_dec"}, format="json").data
    Attempt.objects.filter(id=a["id"]).update(deadline_at=timezone.now() - timedelta(minutes=5))
    call_command("submit_expired_attempts")
    assert Attempt.objects.get(id=a["id"]).status == "expired"


def test_sectional_topic_and_custom_attempts(api):
    s = api.post(f"{V1}/attempts/", {"mode": "sectional", "exam": "iba_mba_2016_dec", "section_no": 2},
                 format="json").data
    assert {q["section_no"] for q in s["questions"]} == {2} and s["time_limit_seconds"]

    topic = Topic.objects.filter(questions__answer_status__in=["verified", "derived"],
                                 questions__answer_kind="mcq").distinct().first()
    t = api.post(f"{V1}/attempts/", {"mode": "topic", "topics": [str(topic.id)], "count": 5}, format="json").data
    assert 1 <= len(t["questions"]) <= 5 and all(q["topic"]["id"] == str(topic.id) for q in t["questions"])
    assert t["time_limit_seconds"] is None  # practice is untimed by default

    c = api.post(f"{V1}/attempts/", {"mode": "custom", "subject": "language", "type": "fill_blank", "count": 10,
                                     "timed": True}, format="json").data
    assert len(c["questions"]) == 10 and c["time_limit_seconds"] == 600
    assert {q["type"] for q in c["questions"]} == {"fill_blank"}


@pytest.mark.parametrize("payload", [
    {"mode": "mock_full"},
    {"mode": "sectional", "exam": "iba_mba_2016_dec"},
    {"mode": "topic"},
    {"mode": "custom", "subject": "writing"},  # essays are never scorable
    {"mode": "nope"},
])
def test_invalid_attempt_requests_are_400(api, payload):
    assert api.post(f"{V1}/attempts/", payload, format="json").status_code in (400, 404)


def test_attempts_only_contain_scorable_questions(api):
    a = api.post(f"{V1}/attempts/", {"mode": "past_paper", "exam": "iba_mba_2015_june"}, format="json").data
    ids = [q["id"] for q in a["questions"]]
    assert Question.objects.filter(id__in=ids).exclude(answer_status__in=["verified", "derived"]).count() == 0
    assert all(q["type"] != "essay" for q in a["questions"])


# ---- bookmarks --------------------------------------------------------------------------------------------

def test_bookmarks_create_list_delete_and_are_idempotent(api):
    q = Question.objects.filter(answer_status="verified").first()
    assert api.post(f"{V1}/bookmarks/", {"question_id": str(q.id)}, format="json").status_code == 201
    assert api.post(f"{V1}/bookmarks/", {"question_id": str(q.id)}, format="json").status_code == 201
    listing = api.get(f"{V1}/bookmarks/").data
    assert listing["count"] == 1 and listing["results"][0]["question"]["id"] == str(q.id)
    assert client_for("other@example.com").get(f"{V1}/bookmarks/").data["count"] == 0
    assert api.delete(f"{V1}/bookmarks/{q.id}/").status_code == 204
    assert api.get(f"{V1}/bookmarks/").data["count"] == 0


def test_page_size_query_param_is_honoured(api):
    r = api.get(f"{V1}/questions/", {"page_size": 7})
    assert len(r.data["results"]) == 7 and r.data["count"] == 741


def test_health_endpoint_reports_database_status(client, monkeypatch):
    assert client.get("/health/").json() == {"status": "ok"}
    from django.db import connection

    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(connection, "cursor", boom)
    assert client.get("/health/").status_code == 503
