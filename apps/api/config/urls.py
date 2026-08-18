from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView

from health import health_check


def api_root(request):
    return JsonResponse(
        {
            "service": "Data Driven Dojô API",
            "version": "1.0",
            "status": "online",
            "docs": "/api/",
            "health": "/health/",
        }
    )


urlpatterns = [
    path("", api_root, name="api-root"),
    path("health/", health_check, name="health-check"),
    path(
        "home/",
        RedirectView.as_view(url="/admin/", permanent=False),
    ),
    path("admin/", admin.site.urls),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/", include("api.urls")),
    path("api/ai/", include("ai.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT,
)
