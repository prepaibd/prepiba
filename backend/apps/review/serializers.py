from rest_framework import serializers

from apps.catalog.models import Option, Question

from . import fidelity
from .models import ReviewLog


class ReviewOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["label", "text", "text_bn", "is_correct"]


class ReviewQuestionSerializer(serializers.ModelSerializer):
    exam = serializers.CharField(source="section.exam.slug", read_only=True)
    session = serializers.CharField(source="section.exam.session", read_only=True)
    section_no = serializers.IntegerField(source="section.section_no", read_only=True)
    subject = serializers.CharField(source="section.subject.slug", read_only=True)
    topic = serializers.CharField(source="topic.name", read_only=True, default=None)
    options = ReviewOptionSerializer(many=True, read_only=True)
    passage = serializers.CharField(source="group.passage", read_only=True, default="")
    solution_en = serializers.SerializerMethodField()
    solution_bn = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "exam", "session", "section_no", "number", "subject", "topic", "type", "stem", "stem_bn",
                  "bn_status", "options", "passage", "answer_status", "answer_source", "source_defect",
                  "review_note", "solution_en", "solution_bn"]

    def get_solution_en(self, q):
        return getattr(getattr(q, "solution", None), "body_en", "")

    def get_solution_bn(self, q):
        return getattr(getattr(q, "solution", None), "body_bn", "")


class ReviewEditSerializer(serializers.Serializer):
    """Reviewable fields. Anything absent is left alone."""

    stem_bn = serializers.CharField(required=False, allow_blank=True)
    bn_status = serializers.ChoiceField(choices=["draft", "reviewed"], required=False)
    options_bn = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False)
    solution_body_bn = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        q: Question = self.context["question"]
        errors = []
        if "stem_bn" in data and data["stem_bn"].strip():
            errors += fidelity.problems(q.stem, data["stem_bn"], "stem")
        labels = {o.label: o for o in q.options.all()}
        for label, text in data.get("options_bn", {}).items():
            if label not in labels:
                raise serializers.ValidationError({"options_bn": f"No option {label}"})
            if text.strip():
                errors += fidelity.problems(labels[label].text, text, f"option {label}")
        if errors:
            raise serializers.ValidationError({"fidelity": errors})
        final_stem = data.get("stem_bn", q.stem_bn)
        if data.get("bn_status") == "reviewed" and not final_stem.strip():
            raise serializers.ValidationError({"bn_status": "Cannot mark reviewed: there is no Bangla stem."})
        return data


def log_changes(user, question, changes: dict[str, tuple[str, str]]):
    ReviewLog.objects.bulk_create([
        ReviewLog(user=user, question=question, field=f, old=old, new=new)
        for f, (old, new) in changes.items() if old != new
    ])


class AnswerVerifySerializer(serializers.Serializer):
    """A reviewer's decision about a question's answer key."""

    answer_status = serializers.ChoiceField(choices=["verified", "derived", "unverified", "disputed"])
    correct_label = serializers.CharField(max_length=2, required=False)

    def validate(self, data):
        q: Question = self.context["question"]
        if q.answer_kind != Question.AnswerKind.MCQ:
            raise serializers.ValidationError("Only multiple-choice answers can be verified here.")
        labels = {o.label for o in q.options.all()}
        label = data.get("correct_label", next((o.label for o in q.options.all() if o.is_correct), None))
        if label is not None and label not in labels:
            raise serializers.ValidationError({"correct_label": f"No option {label}"})
        if data["answer_status"] in ("verified", "derived") and label is None:
            raise serializers.ValidationError({"correct_label": "Choose the correct option first."})
        data["_label"] = label
        return data
