from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("review/questions", views.ReviewQuestionViewSet, basename="review-question")
urlpatterns = router.urls
