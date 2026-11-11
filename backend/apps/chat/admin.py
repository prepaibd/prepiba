from django.contrib import admin

from .models import ChatMessage, ChatSession

admin.site.register([ChatSession, ChatMessage])
