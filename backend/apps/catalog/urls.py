from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("subjects", views.SubjectViewSet, basename="subject")
router.register("topics", views.TopicViewSet, basename="topic")
router.register("exams", views.ExamViewSet, basename="exam")
router.register("questions", views.QuestionViewSet, basename="question")
router.register("formulas", views.FormulaViewSet, basename="formula")
router.register("rules", views.RuleViewSet, basename="rule")
urlpatterns = router.urls
