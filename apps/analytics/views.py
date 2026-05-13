from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.viewsets import ViewSet

from apps.analytics.serializers import (
    FrontendAnalyticsEventInputSerializer,
    FrontendAnalyticsEventOutputSerializer,
)
from apps.analytics.services import registrar_frontend_analytics_event
from apps.core.api.serializers import ErrorResponseSerializer


class FrontendAnalyticsEventThrottle(SimpleRateThrottle):
    scope = "frontend_analytics_event"
    rate = "60/min"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.user.pk,
        }


class FrontendAnalyticsViewSet(ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [FrontendAnalyticsEventThrottle]

    @extend_schema(
        operation_id="analytics_events_create",
        tags=["analytics"],
        description=(
            "Registra evento interno de analytics do frontend sem PII. "
            "Usuário e papel são derivados da sessão autenticada."
        ),
        request=FrontendAnalyticsEventInputSerializer(),
        responses={
            201: FrontendAnalyticsEventOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            429: ErrorResponseSerializer(),
        },
    )
    def create(self, request):
        serializer = FrontendAnalyticsEventInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = registrar_frontend_analytics_event(
            usuario=request.user,
            **serializer.validated_data,
        )
        return Response(
            FrontendAnalyticsEventOutputSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )
