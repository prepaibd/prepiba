"""What the tutor is told about a question, and when it is allowed to know the answer."""
from django.utils import timezone

from apps.catalog.models import Question
from apps.practice.models import Attempt, AttemptQuestion


def answer_may_be_revealed(user, question: Question) -> bool:
    """False while the question sits in one of the user's running exams: the tutor must not leak the key."""
    now = timezone.now()
    running = AttemptQuestion.objects.filter(
        attempt__user=user, attempt__status=Attempt.Status.IN_PROGRESS, question=question,
    ).exclude(attempt__deadline_at__lte=now)
    return not running.exists()


def question_context(question: Question, reveal: bool) -> str:
    lines = [f"Paper: {question.section.exam.session}, section {question.section.section_no}, "
             f"question {question.number} ({question.type.replace('_', ' ')})"]
    g = question.group
    if g and g.instruction:
        lines.append(f"Instructions: {g.instruction}")
    if g and g.passage:
        lines.append(f"Passage:\n{g.passage}")
    lines.append(f"Question: {question.stem}")
    opts = list(question.options.all())
    if opts:
        lines.append("Options:\n" + "\n".join(f"{o.label}. {o.text}" for o in opts))
    if not reveal:
        lines.append("NOTE: the student is in the middle of a timed exam on this question. Give hints and teach "
                     "the method, but do not state or confirm the correct option.")
        return "\n".join(lines)
    correct = next((o for o in opts if o.is_correct), None)
    if correct:
        lines.append(f"Answer key: {correct.label}. {correct.text}")
    elif question.answer_text:
        lines.append(f"Answer key: {question.answer_text}")
    status = question.answer_status
    if status in ("unverified", "disputed"):
        lines.append(f"CAUTION: this answer key is {status}; say so if relevant.")
    if question.source_defect:
        lines.append(f"CAUTION: the printed question is flawed: {question.source_defect}")
    sol = getattr(question, "solution", None)
    if sol and sol.body_en:
        lines.append(f"Reference solution: {sol.body_en}")
    return "\n".join(lines)
