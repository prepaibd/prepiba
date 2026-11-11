from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("attempts", views.AttemptViewSet, basename="attempt")
router.register("bookmarks", views.BookmarkViewSet, basename="bookmark")
urlpatterns = router.urls
