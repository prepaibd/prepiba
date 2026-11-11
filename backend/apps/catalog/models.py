"""Catalog: curriculum, past-paper structure, questions and learning content.

Shaped by the prepiba data: exams hold sections, sections hold groups (shared
passage / instruction) and questions; a question is unique by (section, number).
"""
import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Program(models.TextChoices):
    MBA = "mba"
    BBA = "bba"


class Subject(UUIDModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    name_bn = models.CharField(max_length=100, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "slug"]

    def __str__(self):
        return self.name


class Topic(UUIDModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    slug = models.SlugField(max_length=120)
    name = models.CharField(max_length=160)
    name_bn = models.CharField(max_length=160, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["subject__order", "order", "slug"]
        constraints = [models.UniqueConstraint(fields=["subject", "slug"], name="uniq_topic_subject_slug")]

    def __str__(self):
        return self.name


class Exam(UUIDModel):
    class Completeness(models.TextChoices):
        FULL = "full"
        PARTIAL = "partial"

    slug = models.SlugField(unique=True)  # e.g. iba_mba_2016_dec
    program = models.CharField(max_length=3, choices=Program.choices, default=Program.MBA)
    institute = models.CharField(max_length=60, default="IBA (DU)")
    session = models.CharField(max_length=30)  # "Dec 2017"
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    source_pdf = models.CharField(max_length=255, blank=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    negative_mark = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    completeness = models.CharField(max_length=8, choices=Completeness.choices, default=Completeness.PARTIAL)
    parts_marks = models.JSONField(default=dict, blank=True)
    unresolved_notes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.institute} {self.program.upper()} {self.session}"


class ExamSection(UUIDModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sections")
    part_label = models.CharField(max_length=60, blank=True)
    section_no = models.PositiveSmallIntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="sections")
    label = models.CharField(max_length=160, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "section_no"]
        constraints = [models.UniqueConstraint(fields=["exam", "section_no"], name="uniq_section_per_exam")]

    def __str__(self):
        return f"{self.exam.slug} / S{self.section_no}"


class QuestionGroup(UUIDModel):
    class GroupType(models.TextChoices):
        STANDALONE = "standalone"
        PASSAGE = "passage"
        DATA_SUFFICIENCY = "data_sufficiency"
        PUZZLE = "puzzle"

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="groups")
    order = models.PositiveSmallIntegerField(default=0)
    group_type = models.CharField(max_length=20, choices=GroupType.choices, default=GroupType.STANDALONE)
    source_label = models.CharField(max_length=160, blank=True)
    instruction = models.TextField(blank=True)
    instruction_bn = models.TextField(blank=True)
    passage = models.TextField(blank=True)
    passage_bn = models.TextField(blank=True)
    table = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["section", "order"], name="uniq_group_order_per_section")]


class Question(UUIDModel):
    class Type(models.TextChoices):
        PROBLEM_SOLVING = "problem_solving"
        PUZZLE = "puzzle"
        FILL_BLANK = "fill_blank"
        SENTENCE_CORRECTION = "sentence_correction"
        READING_COMP = "reading_comp"
        DATA_SUFFICIENCY = "data_sufficiency"
        WORD_SUBSTITUTION = "word_substitution"
        ERROR_IDENTIFICATION = "error_identification"
        CRITICAL_REASONING = "critical_reasoning"
        ESSAY = "essay"
        SYNONYM = "synonym"
        ANTONYM = "antonym"
        ARGUMENT = "argument"
        PASSAGE_COMPLETION = "passage_completion"

    class AnswerKind(models.TextChoices):
        MCQ = "mcq"  # one of the options
        TEXT = "text"  # numeric / free-response, stored in answer_text
        ESSAY = "essay"  # no key

    class AnswerStatus(models.TextChoices):
        VERIFIED = "verified"  # key printed in PDF, or two independent passes agree
        DERIVED = "derived"  # derived once by the solution layer
        UNVERIFIED = "unverified"  # legacy key, no provenance
        DISPUTED = "disputed"  # conflicting / ambiguous key
        NONE = "none"  # essays

    class ReviewStatus(models.TextChoices):
        DRAFT = "draft"
        IN_REVIEW = "in_review"
        PUBLISHED = "published"

    section = models.ForeignKey(ExamSection, on_delete=models.CASCADE, related_name="questions")
    group = models.ForeignKey(QuestionGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    number = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(default=0)
    type = models.CharField(max_length=24, choices=Type.choices)
    stem = models.TextField()
    stem_bn = models.TextField(blank=True)
    bn_status = models.CharField(max_length=12, blank=True)  # draft / reviewed
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    answer_kind = models.CharField(max_length=8, choices=AnswerKind.choices)
    answer_text = models.CharField(max_length=500, blank=True)
    answer_status = models.CharField(max_length=12, choices=AnswerStatus.choices, default=AnswerStatus.UNVERIFIED)
    answer_source = models.CharField(max_length=40, blank=True)
    answer_prev = models.CharField(max_length=500, blank=True)
    source_defect = models.TextField(blank=True)  # printed question is broken
    review_note = models.TextField(blank=True)  # assumption / ambiguity flagged during solving
    review_status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)

    class Meta:
        ordering = ["order", "number"]
        constraints = [models.UniqueConstraint(fields=["section", "number"], name="uniq_question_number_per_section")]
        indexes = [models.Index(fields=["type"]), models.Index(fields=["answer_status"])]

    def __str__(self):
        return f"{self.section.exam.slug} {self.section.section_no}-{self.number}"

    @property
    def is_scorable(self):
        """Only trusted multiple-choice keys count towards a score."""
        return (
            self.answer_kind == self.AnswerKind.MCQ
            and self.answer_status in (self.AnswerStatus.VERIFIED, self.AnswerStatus.DERIVED)
            and not self.source_defect
        )


class Option(UUIDModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=2)  # canonical A-E
    label_display = models.CharField(max_length=8, blank=True)  # printed symbol if not a letter
    text = models.TextField()
    text_bn = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        constraints = [models.UniqueConstraint(fields=["question", "label"], name="uniq_option_label")]


class Figure(UUIDModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True, related_name="figures")
    group = models.ForeignKey(QuestionGroup, on_delete=models.CASCADE, null=True, blank=True, related_name="figures")
    fig_id = models.CharField(max_length=60)
    role = models.CharField(max_length=20, default="question")
    image = models.CharField(max_length=255)  # path relative to MEDIA_ROOT
    caption = models.CharField(max_length=300, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(question__isnull=False) | models.Q(group__isnull=False),
                name="figure_has_owner",
            )
        ]


class Formula(UUIDModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    body_bn = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)  # original card, kept verbatim


class GrammarRule(UUIDModel):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    body_bn = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)


class Solution(UUIDModel):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="solution")
    body_en = models.TextField(blank=True)
    body_bn = models.TextField(blank=True)
    trap_en = models.TextField(blank=True)
    trap_bn = models.TextField(blank=True)
    trick_en = models.TextField(blank=True)
    trick_bn = models.TextField(blank=True)
    note = models.TextField(blank=True)
    formulas = models.ManyToManyField(Formula, blank=True, related_name="solutions")
    rules = models.ManyToManyField(GrammarRule, blank=True, related_name="solutions")
