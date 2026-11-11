from django.contrib import admin

from . import models


class OptionInline(admin.TabularInline):
    model = models.Option
    extra = 0


@admin.register(models.Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "type", "answer_status", "review_status", "topic"]
    list_filter = ["type", "answer_status", "review_status", "section__exam"]
    search_fields = ["stem"]
    inlines = [OptionInline]


admin.site.register([models.Subject, models.Topic, models.Exam, models.ExamSection, models.QuestionGroup,
                     models.Figure, models.Formula, models.GrammarRule, models.Solution])
