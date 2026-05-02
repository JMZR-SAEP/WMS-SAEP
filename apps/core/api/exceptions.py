from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class DomainConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "domain_conflict"
    default_detail = "Conflito de domínio."

    def __init__(self, detail=None, code=None, *, details=None):
        super().__init__(detail=detail or self.default_detail, code=code)
        self.details_payload = details


def api_exception_handler(exc, context):
    """Custom exception handler for API responses."""
    response = exception_handler(exc, context)
    request = context.get("request") if context else None

    if response is None:
        trace_id = getattr(exc, "trace_id", None)
        if trace_id is None and request is not None:
            trace_id = request.META.get("HTTP_X_TRACE_ID")

        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Erro interno do servidor",
                    "details": None,
                    "trace_id": trace_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    details = getattr(exc, "details_payload", None)
    if details is None and isinstance(response.data, dict) and "detail" not in response.data:
        details = response.data

    trace_id = None
    if isinstance(response.data, dict):
        trace_id = response.data.get("trace_id")
    if trace_id is None:
        trace_id = getattr(exc, "trace_id", None)
    if trace_id is None and request is not None:
        trace_id = request.META.get("HTTP_X_TRACE_ID")

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        code = "validation_error"
        message = "Dados inválidos."
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        code = (
            getattr(exc, "default_code", None)
            or getattr(exc, "code", None)
            or getattr(detail, "code", None)
            or "api_error"
        )
        message = str(detail or exc)

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "trace_id": trace_id,
        }
    }

    return response
