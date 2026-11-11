from django.contrib import admin

from .models import ReviewLog


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "question", "field"]
    readonly_fields = [f.name for f in ReviewLog._meta.fields]

    def has_add_permission(self, request):
        return False
