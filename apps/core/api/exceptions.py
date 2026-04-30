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

    if response is None:
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Erro interno do servidor",
                    "details": None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, APIException):
        details = getattr(exc, "details_payload", None)
        if details is None and isinstance(response.data, dict) and "detail" not in response.data:
            details = response.data

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            code = "validation_error"
            message = "Dados inválidos."
        else:
            code = getattr(exc, "default_code", None) or getattr(exc, "code", "api_error")
            if isinstance(response.data, dict):
                message = str(response.data.get("detail", str(exc)))
            else:
                message = str(exc)

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        }

    return response
