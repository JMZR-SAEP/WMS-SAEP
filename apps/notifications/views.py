from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.helpers import forced_singular_serializer
from drf_spectacular.openapi import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.api.serializers import ErrorResponseSerializer
from apps.notifications.models import Notificacao
from apps.notifications.policies import queryset_notificacoes_visiveis
from apps.notifications.serializers import (
    NotificacaoListPaginatedSerializer,
    NotificacaoOutputSerializer,
    NotificacaoUnreadCountOutputSerializer,
    PushConfigOutputSerializer,
    PushSubscriptionDeactivateInputSerializer,
    PushSubscriptionInputSerializer,
    PushSubscriptionOutputSerializer,
)
from apps.notifications.services import (
    contar_notificacoes_individuais_nao_lidas,
    desativar_push_subscription,
    marcar_notificacao_como_lida,
    registrar_push_subscription,
)


class NotificacaoViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificacaoOutputSerializer
    queryset = Notificacao.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return queryset_notificacoes_visiveis(self.request.user)

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(
        operation_id="notifications_list",
        tags=["notifications"],
        description=(
            "Lista paginada das notificações visíveis ao usuário autenticado. "
            "Inclui notificações individuais do usuário e notificações coletivas do papel atual."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                description="Número da página (padrão: 1)",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="page_size",
                description="Quantidade de resultados por página (padrão: 20, máximo: 100)",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: forced_singular_serializer(NotificacaoListPaginatedSerializer),
            403: ErrorResponseSerializer(),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        operation_id="notifications_mark_read",
        tags=["notifications"],
        request=None,
        responses={
            200: NotificacaoOutputSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notificacao = marcar_notificacao_como_lida(
            notificacao=self.get_object(),
            usuario=request.user,
        )
        return Response(NotificacaoOutputSerializer(notificacao).data)

    @extend_schema(
        operation_id="notifications_unread_count",
        tags=["notifications"],
        description=(
            "Retorna o contador de notificações individuais não lidas do usuário autenticado. "
            "Notificações coletivas por papel não entram nesse contador."
        ),
        responses={
            200: NotificacaoUnreadCountOutputSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        unread_count = contar_notificacoes_individuais_nao_lidas(usuario=request.user)
        return Response({"unread_count": unread_count})

    @extend_schema(
        operation_id="notifications_push_config",
        tags=["notifications"],
        description="Retorna configuração pública de Web Push para o usuário autenticado.",
        responses={
            200: PushConfigOutputSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["get"], url_path="push/config")
    def push_config(self, request):
        public_key = getattr(settings, "WEB_PUSH_VAPID_PUBLIC_KEY", "")
        return Response(
            {
                "enabled": bool(public_key),
                "vapid_public_key": public_key,
            }
        )

    @extend_schema(
        operation_id="notifications_push_subscriptions",
        tags=["notifications"],
        description="Registra ou atualiza a assinatura Web Push do usuário autenticado.",
        request=PushSubscriptionInputSerializer(),
        responses={
            200: PushSubscriptionOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["post"], url_path="push/subscriptions")
    def push_subscriptions(self, request):
        serializer = PushSubscriptionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        keys = serializer.validated_data["keys"]
        subscription = registrar_push_subscription(
            usuario=request.user,
            endpoint=serializer.validated_data["endpoint"],
            p256dh=keys["p256dh"],
            auth=keys["auth"],
        )
        return Response(PushSubscriptionOutputSerializer(subscription).data)

    @extend_schema(
        operation_id="notifications_push_subscriptions_deactivate",
        tags=["notifications"],
        description="Desativa uma assinatura Web Push do usuário autenticado pelo endpoint.",
        request=PushSubscriptionDeactivateInputSerializer(),
        responses={
            204: None,
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["post"], url_path="push/subscriptions/deactivate")
    def push_subscriptions_deactivate(self, request):
        serializer = PushSubscriptionDeactivateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        desativar_push_subscription(
            usuario=request.user,
            endpoint=serializer.validated_data["endpoint"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
