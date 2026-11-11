from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(_request):
    """Liveness + database reachability, for container health checks and uptime monitors."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:  # any DB failure means "not ready"
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.practice.urls")),
    path("api/v1/", include("apps.review.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.ai.urls")),
    path("api/v1/", include("apps.chat.urls")),
    path("api/v1/", include("apps.writing.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
