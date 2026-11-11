from django.contrib import admin

from .models import AIUsageLog


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "kind", "status", "model", "prompt_chars", "output_chars"]
    list_filter = ["kind", "status"]
