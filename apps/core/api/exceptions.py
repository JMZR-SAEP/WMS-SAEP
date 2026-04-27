from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Custom exception handler for API responses."""
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "Erro interno do servidor",
                    "details": None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, APIException):
        response.data = {
            "error": {
                "code": getattr(exc, "code", "api_error"),
                "message": str(response.data.get("detail", str(exc))),
                "details": response.data if response.status_code != 400 else None,
            }
        }

    return response
