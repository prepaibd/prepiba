from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("chat/sessions", views.SessionViewSet, basename="chat-session")
urlpatterns = [
    path("chat/sessions/<uuid:pk>/messages/", views.MessageStreamView.as_view()),
    *router.urls,
]
