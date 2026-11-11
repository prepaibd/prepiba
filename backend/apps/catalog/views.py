from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import serializers as s
from .models import Exam, ExamSection, Formula, GrammarRule, Question, Subject, Topic


def scorable_filter(prefix: str = "") -> Q:
    """Q matching trusted multiple-choice questions (mirror of Question.is_scorable).

    `prefix` is the lookup path to the question from another model, e.g. "questions__".
    """
    return Q(**{
        f"{prefix}answer_kind": Question.AnswerKind.MCQ,
        f"{prefix}answer_status__in": [Question.AnswerStatus.VERIFIED, Question.AnswerStatus.DERIVED],
        f"{prefix}source_defect": "",
    })


def scorable_questions():
    return Question.objects.filter(scorable_filter())


def question_queryset():
    return (Question.objects.select_related("section__exam", "section__subject", "topic__subject", "group")
            .prefetch_related("options", "figures"))


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = s.SubjectSerializer
    pagination_class = None


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Topic.objects.select_related("subject").annotate(question_count=Count("questions"))
    serializer_class = s.TopicSerializer
    pagination_class = None
    filterset_fields = ["subject__slug"]


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        return Exam.objects.annotate(
            question_count=Count("sections__questions", distinct=True),
            scorable_count=Count("sections__questions", filter=scorable_filter("sections__questions__"),
                                 distinct=True),
        )

    def get_serializer_class(self):
        return s.ExamDetailSerializer if self.action == "retrieve" else s.ExamSerializer

    def retrieve(self, request, *args, **kwargs):
        exam = self.get_object()
        sections = ExamSection.objects.filter(exam=exam).select_related("subject").annotate(
            question_count=Count("questions", distinct=True),
            scorable_count=Count("questions", filter=scorable_filter("questions__"), distinct=True)).order_by("order")
        data = s.ExamSerializer(exam).data
        data["sections"] = s.SectionSerializer(sections, many=True).data
        return Response(data)


class QuestionFilter(filters.FilterSet):
    exam = filters.CharFilter(field_name="section__exam__slug")
    section_no = filters.NumberFilter(field_name="section__section_no")
    subject = filters.CharFilter(field_name="section__subject__slug")
    topic = filters.UUIDFilter(field_name="topic_id")
    type = filters.CharFilter()
    answer_status = filters.CharFilter()
    search = filters.CharFilter(method="filter_search")

    def filter_search(self, qs, name, value):
        """Every whitespace-separated word must appear in the stem, an option, or the shared passage."""
        for word in value.split()[:8]:
            qs = qs.filter(Q(stem__icontains=word) | Q(options__text__icontains=word)
                           | Q(group__passage__icontains=word) | Q(group__instruction__icontains=word))
        return qs.distinct()

    class Meta:
        model = Question
        fields = []


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = s.QuestionSerializer
    filterset_class = QuestionFilter

    def get_queryset(self):
        return question_queryset().order_by("section__exam__year", "section__exam__month",
                                            "section__section_no", "order")

    @action(detail=True, methods=["get"])
    def solution(self, request, pk=None):
        q = get_object_or_404(question_queryset().select_related("solution"), pk=pk)
        return Response(s.reveal(q, request))


class FormulaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Formula.objects.order_by("title")
    serializer_class = s.FormulaSerializer
    lookup_field = "slug"
    pagination_class = None


class RuleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GrammarRule.objects.order_by("title")
    serializer_class = s.RuleSerializer
    lookup_field = "slug"
    pagination_class = None

