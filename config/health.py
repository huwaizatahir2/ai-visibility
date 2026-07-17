from __future__ import annotations

from django.db import DatabaseError
from django.db import connection
from django.http import HttpRequest
from django.http import JsonResponse


def healthz(_request: HttpRequest) -> JsonResponse:
    """Liveness + DB connectivity check for load balancers and deploy scripts."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "error", "db": False}, status=503)
    return JsonResponse({"status": "ok", "db": True})
