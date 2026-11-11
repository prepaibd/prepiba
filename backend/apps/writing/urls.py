from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("writing/prompts", views.PromptViewSet, basename="writing-prompt")
router.register("writing/submissions", views.SubmissionViewSet, basename="writing-submission")
urlpatterns = router.urls
