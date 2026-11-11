from django.contrib import admin

from .models import Attempt, AttemptQuestion, Bookmark


class ItemInline(admin.TabularInline):
    model = AttemptQuestion
    extra = 0
    raw_id_fields = ["question"]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "mode", "exam", "status", "score", "started_at"]
    list_filter = ["mode", "status"]
    inlines = [ItemInline]


admin.site.register(Bookmark)
