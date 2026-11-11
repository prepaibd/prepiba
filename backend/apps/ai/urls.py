from django.urls import path

from . import views

urlpatterns = [path("ai/usage/", views.UsageView.as_view())]
