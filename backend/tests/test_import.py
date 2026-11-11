import pytest

from apps.catalog.importer import import_all
from apps.catalog.models import Exam, Figure, Formula, GrammarRule, Option, Question, QuestionGroup, Solution


@pytest.fixture
def imported(db):
    """The catalog is imported once per test session (see conftest.django_db_setup)."""


def q(exam, section, number):
    return Question.objects.get(section__exam__slug=exam, section__section_no=section, number=number)


def test_totals(imported):
    assert Exam.objects.count() == 14
    assert Question.objects.count() == 741
    assert QuestionGroup.objects.count() == 120
    assert Figure.objects.count() == 13
    assert Solution.objects.count() == 741
    assert Formula.objects.count() == 22
    assert GrammarRule.objects.count() == 26


def test_every_question_has_a_topic_and_a_unique_key(imported):
    assert Question.objects.filter(topic__isnull=True).count() == 0


def test_import_is_idempotent(db):
    counts = (Exam.objects.count(), Question.objects.count(), Option.objects.count(), Figure.objects.count())
    second = import_all()
    assert (Exam.objects.count(), Question.objects.count(), Option.objects.count(), Figure.objects.count()) == counts
    assert second.questions == 741


def test_stem_prefix_stripped_and_mcq_key_set(imported):
    question = q("iba_mba_2017_dec", 1, 10)
    assert not question.stem.lstrip().startswith("10.")
    assert question.type == "error_identification"
    assert question.options.count() == 5
    assert question.options.get(is_correct=True).label == "D"
    assert question.answer_status == "verified"
    assert question.is_scorable


def test_every_scorable_question_has_exactly_one_correct_option(imported):
    for question in Question.objects.filter(answer_kind="mcq", answer_status__in=["verified", "derived"]):
        assert question.options.filter(is_correct=True).count() == 1, question


def test_essay_has_no_key_and_is_not_scorable(imported):
    essay = Question.objects.filter(type="essay").first()
    assert essay.answer_kind == "essay" and essay.answer_status == "none"
    assert not essay.is_scorable
    assert essay.options.count() == 0


def test_data_sufficiency_gets_five_canonical_options(imported):
    ds = Question.objects.filter(type="data_sufficiency", answer_kind="mcq").first()
    assert sorted(ds.options.values_list("label", flat=True)) == list("ABCDE")


def test_free_response_is_text_kind_and_not_scorable(imported):
    free = q("iba_mba_2021_dec", 1, 13)
    assert free.answer_kind == "text" and free.answer_text
    assert free.options.count() == 0 and not free.is_scorable


def test_multi_answer_is_disputed_and_excluded_from_scoring(imported):
    question = q("iba_mba_2020_dec", 3, 34)
    assert question.answer_status == "disputed"
    assert not question.is_scorable
    assert not question.options.filter(is_correct=True).exists()


def test_true_key_conflict_is_disputed_and_keeps_previous(imported):
    question = q("iba_mba_2015_june", 2, 33)
    assert question.answer_status == "disputed" and question.answer_prev == "C"


def test_source_defect_is_never_scorable(imported):
    defects = Question.objects.exclude(source_defect="")
    assert defects.count() == 7
    assert not any(d.is_scorable for d in defects)


def test_figure_file_copied_to_media(imported, settings):
    fig = Figure.objects.first()
    assert (settings.MEDIA_ROOT / fig.image).exists()


def test_group_passage_and_bangla_layers(imported):
    assert Question.objects.exclude(stem_bn="").count() == 493
    assert q("iba_mba_2017_dec", 2, 26).stem_bn


def test_papers_marked_full_only_when_complete(imported):
    assert Exam.objects.get(slug="iba_mba_2016_dec").completeness == "full"
    assert Exam.objects.get(slug="iba_mba_2023_dec").completeness == "partial"
    assert Exam.objects.get(slug="iba_mba_2020_dec").total_marks is None


def test_solution_links_to_formulas(imported):
    assert Solution.objects.filter(formulas__isnull=False).distinct().count() > 100


def test_no_review_notes_are_lost(imported):
    """SOLUTION_NOTES.md has 119 note rows over 88 questions; 31 questions appear in both tables."""
    assert Question.objects.exclude(review_note="").count() == 88
    assert Question.objects.filter(review_note__contains=" | ").count() == 31
