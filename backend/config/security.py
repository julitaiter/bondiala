from rest_framework.authentication import SessionAuthentication


class CsrfSessionAuthentication(SessionAuthentication):
    """También protege login/registro, antes de que exista una sesión."""

    def authenticate(self, request):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.enforce_csrf(request)
        return super().authenticate(request)


def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_exception_handler

    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {"error": response.data}
    return response
