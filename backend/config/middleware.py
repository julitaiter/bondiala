import logging
from django.http import JsonResponse

logger = logging.getLogger("bondiala.security")


class ResponseHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "private, no-store"
            response["Vary"] = "Cookie"
            response["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
        response["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if response.status_code in {403, 429} or response.status_code >= 500:
            logger.warning(
                "http_event status=%s path=%s", response.status_code, request.path
            )
        return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "detail": "La sesión de seguridad venció. Recargá e intentá de nuevo."
            }
        },
        status=403,
    )
