from django.conf import settings
from rest_framework import serializers

from .models import (
    Exam,
    ExamSection,
    Figure,
    Formula,
    GrammarRule,
    Option,
    Question,
    QuestionGroup,
    Solution,
    Subject,
    Topic,
)


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "slug", "name", "name_bn"]


class TopicSerializer(serializers.ModelSerializer):
    subject = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    question_count = serializers.IntegerField(read_only=True)  # only present on the /topics/ list

    class Meta:
        model = Topic
        fields = ["id", "slug", "name", "name_bn", "subject", "question_count"]


class SectionSerializer(serializers.ModelSerializer):
    subject = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    scorable_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ExamSection
        fields = ["section_no", "part_label", "label", "subject", "question_count", "scorable_count"]


class ExamSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    scorable_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = ["slug", "program", "institute", "session", "year", "month", "completeness", "question_count",
                  "scorable_count", "duration_minutes", "total_marks"]


class ExamDetailSerializer(ExamSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta(ExamSerializer.Meta):
        fields = ExamSerializer.Meta.fields + ["sections"]


class OptionSerializer(serializers.ModelSerializer):
    """Deliberately omits is_correct: answers are only revealed via solutions / results."""

    class Meta:
        model = Option
        fields = ["label", "label_display", "text", "text_bn"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionGroup
        fields = ["id", "group_type", "instruction", "instruction_bn", "passage", "passage_bn", "table"]


class FigureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Figure
        fields = ["url", "caption", "role"]

    def get_url(self, obj):
        path = f"{settings.MEDIA_URL}{obj.image}"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class QuestionSerializer(serializers.ModelSerializer):
    exam = serializers.CharField(source="section.exam.slug", read_only=True)
    section_no = serializers.IntegerField(source="section.section_no", read_only=True)
    subject = serializers.CharField(source="section.subject.slug", read_only=True)
    topic = TopicSerializer(read_only=True)
    options = OptionSerializer(many=True, read_only=True)
    group = GroupSerializer(read_only=True)
    figures = FigureSerializer(many=True, read_only=True)
    scorable = serializers.BooleanField(source="is_scorable", read_only=True)

    class Meta:
        model = Question
        fields = ["id", "exam", "section_no", "number", "subject", "type", "stem", "stem_bn", "bn_status", "topic",
                  "marks", "answer_kind", "answer_status", "scorable", "options", "group", "figures"]


class FormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Formula
        fields = ["slug", "title", "title_bn", "body", "body_bn"]


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrammarRule
        fields = ["slug", "title", "title_bn", "body", "body_bn"]


class SolutionSerializer(serializers.ModelSerializer):
    formulas = FormulaSerializer(many=True, read_only=True)
    rules = RuleSerializer(many=True, read_only=True)

    class Meta:
        model = Solution
        fields = ["body_en", "body_bn", "trap_en", "trap_bn", "trick_en", "trick_bn", "note", "formulas", "rules"]


def reveal(question: Question, request=None) -> dict:
    """Answer + solution for a question (used after answering / in results)."""
    correct = [o.label for o in question.options.all() if o.is_correct]
    sol = getattr(question, "solution", None)
    return {
        "correct_label": correct[0] if correct else None,
        "answer_text": question.answer_text,
        "answer_status": question.answer_status,
        "answer_prev": question.answer_prev,
        "source_defect": question.source_defect,
        "review_note": question.review_note,
        "solution": SolutionSerializer(sol).data if sol else None,
    }
