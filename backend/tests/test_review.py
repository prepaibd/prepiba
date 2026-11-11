import pytest

from apps.catalog.models import Option, Question
from apps.review import fidelity
from apps.review.models import ReviewLog
from tests.helpers import V1, client_for

pytestmark = pytest.mark.django_db


@pytest.fixture
def reviewer():
    return client_for("rev@example.com", role="reviewer")


def bn_question(status="draft"):
    return Question.objects.filter(section__subject__slug="mathematics", bn_status=status).exclude(stem_bn="").first()


# ---- fidelity rules ---------------------------------------------------------------------------------------

def test_fidelity_accepts_faithful_translation():
    assert fidelity.problems("A box has 200 marbles, 15% are black.", "একটি box-এ 200টি marble, 15% কালো।") == []


def test_fidelity_flags_changed_numbers_latex_and_bangla_digits():
    assert any("numbers differ" in p for p in fidelity.problems("It costs 200", "দাম 300"))
    assert any("LaTeX" in p for p in fidelity.problems("Find $x^2$", "খুঁজুন $x^3$"))
    assert any("Bangla digits" in p for p in fidelity.problems("It costs 20", "দাম ২০"))
    assert any("numbers" in p for p in fidelity.problems("no numbers", "এখানে 5 আছে"))


def test_fidelity_ignores_printed_question_number_prefix():
    assert fidelity.problems("26. If SP is 5", "SP 5 হলে") == []


# ---- access -------------------------------------------------------------------------------------------------

def test_students_cannot_use_review_endpoints():
    c = client_for("stu@example.com")
    assert c.get(f"{V1}/review/questions/").status_code == 403
    q = bn_question()
    assert c.patch(f"{V1}/review/questions/{q.id}/", {"bn_status": "reviewed"}, format="json").status_code == 403


def test_anonymous_cannot_use_review_endpoints():
    from rest_framework.test import APIClient

    assert APIClient().get(f"{V1}/review/questions/").status_code == 401


# ---- listing ------------------------------------------------------------------------------------------------

def test_summary_and_filters(reviewer):
    s = reviewer.get(f"{V1}/review/questions/summary/").data
    assert s["bangla"]["draft"] == 493 and s["bangla"]["reviewed"] == 0
    assert s["answers"]["verified"] == 705 and s["flagged"] == 88
    drafts = reviewer.get(f"{V1}/review/questions/", {"bn": "draft", "page_size": 5}).data
    assert drafts["count"] == 493
    missing = reviewer.get(f"{V1}/review/questions/", {"bn": "missing", "page_size": 5}).data
    assert missing["count"] == 741 - 26 - 493  # essays/arguments are never expected to have Bangla
    flagged = reviewer.get(f"{V1}/review/questions/", {"flagged": "1", "page_size": 200}).data
    assert all(q["review_note"] or q["source_defect"] for q in flagged["results"])


def test_reviewers_see_the_answer_key(reviewer):
    q = bn_question()
    data = reviewer.get(f"{V1}/review/questions/{q.id}/").data
    assert any(o["is_correct"] for o in data["options"]) and data["stem"] and data["solution_en"]


# ---- editing ------------------------------------------------------------------------------------------------

def test_valid_edit_is_saved_logged_and_visible_to_students(reviewer):
    q = bn_question()
    new = q.stem_bn + " "  # harmless whitespace-only change would not be logged; add a word instead
    new = q.stem_bn + " (যাচাইকৃত)"
    r = reviewer.patch(f"{V1}/review/questions/{q.id}/", {"stem_bn": new, "bn_status": "reviewed"}, format="json")
    assert r.status_code == 200 and r.data["bn_status"] == "reviewed" and r.data["stem_bn"] == new
    fields = set(ReviewLog.objects.filter(question=q).values_list("field", flat=True))
    assert fields == {"stem_bn", "bn_status"}
    assert ReviewLog.objects.get(question=q, field="stem_bn").old == q.stem_bn
    student = client_for("stu@example.com").get(f"{V1}/questions/{q.id}/").data
    assert student["bn_status"] == "reviewed" and student["stem_bn"] == new


def test_editing_a_reviewed_translation_sends_it_back_to_draft(reviewer):
    q = bn_question()
    reviewer.patch(f"{V1}/review/questions/{q.id}/", {"bn_status": "reviewed"}, format="json")
    r = reviewer.patch(f"{V1}/review/questions/{q.id}/", {"stem_bn": q.stem_bn + " ।"}, format="json")
    assert r.data["bn_status"] == "draft"


def test_unfaithful_translation_is_rejected_and_nothing_changes(reviewer):
    q = bn_question()
    before = (q.stem_bn, ReviewLog.objects.count())
    r = reviewer.patch(f"{V1}/review/questions/{q.id}/", {"stem_bn": "সব সংখ্যা ৯৯৯৯৯", "bn_status": "reviewed"},
                       format="json")
    assert r.status_code == 400 and r.data["fidelity"]
    q.refresh_from_db()
    assert (q.stem_bn, ReviewLog.objects.count()) == before and q.bn_status == "draft"


def test_cannot_mark_reviewed_without_a_bangla_stem(reviewer):
    q = Question.objects.filter(type="fill_blank", stem_bn="").first()
    r = reviewer.patch(f"{V1}/review/questions/{q.id}/", {"bn_status": "reviewed"}, format="json")
    assert r.status_code == 400 and "bn_status" in r.data


def test_option_and_solution_edits(reviewer):
    q = Question.objects.filter(type="problem_solving", options__isnull=False).exclude(stem_bn="").first()
    opt = q.options.first()
    r = reviewer.patch(f"{V1}/review/questions/{q.id}/",
                       {"options_bn": {opt.label: opt.text}, "solution_body_bn": "ধাপে ধাপে সমাধান।"}, format="json")
    assert r.status_code == 200 and r.data["solution_bn"] == "ধাপে ধাপে সমাধান।"
    assert Option.objects.get(pk=opt.pk).text_bn == opt.text
    assert ReviewLog.objects.filter(question=q, field="solution_body_bn").exists()
    bad = reviewer.patch(f"{V1}/review/questions/{q.id}/", {"options_bn": {"Z": "x"}}, format="json")
    assert bad.status_code == 400


def test_put_is_not_allowed(reviewer):
    q = bn_question()
    assert reviewer.put(f"{V1}/review/questions/{q.id}/", {"stem_bn": "x"}, format="json").status_code == 405


# ---- answer verification -------------------------------------------------------------------------------------

def verifiable():
    return Question.objects.filter(answer_kind="mcq", answer_status="verified", type="problem_solving").first()


def test_reviewer_can_change_the_key_and_status(reviewer):
    q = verifiable()
    old = Option.objects.get(question=q, is_correct=True).label
    new = next(o.label for o in q.options.all() if o.label != old)
    r = reviewer.post(f"{V1}/review/questions/{q.id}/answer/", {"answer_status": "disputed", "correct_label": new},
                      format="json")
    assert r.status_code == 200 and r.data["answer_status"] == "disputed"
    assert [o["label"] for o in r.data["options"] if o["is_correct"]] == [new]
    q.refresh_from_db()
    assert (q.answer_source, q.answer_prev) == ("reviewer", old)
    assert set(ReviewLog.objects.filter(question=q).values_list("field", flat=True)) == {"answer_status",
                                                                                         "correct_option"}


def test_disputed_questions_drop_out_of_new_attempts(reviewer):
    q = Question.objects.filter(section__exam__slug="iba_mba_2016_dec", answer_status="verified",
                                answer_kind="mcq").first()
    reviewer.post(f"{V1}/review/questions/{q.id}/answer/", {"answer_status": "disputed"}, format="json")
    a = reviewer.post(f"{V1}/attempts/", {"mode": "past_paper", "exam": "iba_mba_2016_dec"}, format="json").data
    assert str(q.id) not in [x["id"] for x in a["questions"]]


def test_verifying_needs_a_correct_option():
    q = Question.objects.filter(answer_kind="mcq", answer_status="unverified").exclude(options__is_correct=True).first()
    c = client_for("rev2@example.com", role="reviewer")
    bad = c.post(f"{V1}/review/questions/{q.id}/answer/", {"answer_status": "verified"}, format="json")
    assert bad.status_code == 400 and "correct_label" in bad.data
    ok = c.post(f"{V1}/review/questions/{q.id}/answer/",
                {"answer_status": "verified", "correct_label": q.options.first().label}, format="json")
    assert ok.status_code == 200
    q.refresh_from_db()
    assert q.is_scorable


def test_invalid_label_and_non_mcq_are_rejected(reviewer):
    q = verifiable()
    assert reviewer.post(f"{V1}/review/questions/{q.id}/answer/", {"answer_status": "verified", "correct_label": "Z"},
                         format="json").status_code == 400
    essay = Question.objects.filter(type="essay").first()
    assert reviewer.post(f"{V1}/review/questions/{essay.id}/answer/", {"answer_status": "verified"},
                         format="json").status_code == 400


def test_students_cannot_verify_answers():
    q = verifiable()
    assert client_for("stu@example.com").post(f"{V1}/review/questions/{q.id}/answer/",
                                               {"answer_status": "disputed"}, format="json").status_code == 403


def test_reimport_keeps_reviewer_decisions(reviewer):
    from apps.catalog.importer import import_all

    q = verifiable()
    old = Option.objects.get(question=q, is_correct=True).label
    new = next(o.label for o in q.options.all() if o.label != old)
    reviewer.post(f"{V1}/review/questions/{q.id}/answer/", {"answer_status": "verified", "correct_label": new},
                  format="json")
    b = bn_question()
    reviewer.patch(f"{V1}/review/questions/{b.id}/", {"stem_bn": b.stem_bn + " ।", "bn_status": "reviewed"},
                   format="json")
    import_all()
    q.refresh_from_db()
    b.refresh_from_db()
    assert Option.objects.get(question=q, is_correct=True).label == new and q.answer_source == "reviewer"
    assert b.bn_status == "reviewed" and b.stem_bn.endswith(" ।")
    # untouched questions are still refreshed from the data
    other = Question.objects.filter(answer_status="verified").exclude(pk=q.pk).first()
    assert other.answer_source == "legacy+solution_agree"
