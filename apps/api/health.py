from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    """Lightweight readiness/liveness endpoint for deployment and monitoring."""
    checks = {"database": "ok"}
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        checks["database"] = "error"
        status_code = 503

    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "service": "data-dojo-api",
            "checks": checks,
        },
        status=status_code,
    )
