from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.api.serializers import ErrorResponseSerializer
from apps.requisitions.filters import RequisicaoFilter
from apps.requisitions.policies import queryset_requisicoes_visiveis
from apps.requisitions.serializers import (
    RequisicaoAuthorizeInputSerializer,
    RequisicaoCancelInputSerializer,
    RequisicaoCreateInputSerializer,
    RequisicaoDetailOutputSerializer,
    RequisicaoFulfillInputSerializer,
    RequisicaoListOutputSerializer,
    RequisicaoListPaginatedSerializer,
    RequisicaoPendingApprovalOutputSerializer,
    RequisicaoPendingApprovalPaginatedSerializer,
    RequisicaoPendingFulfillmentOutputSerializer,
    RequisicaoPendingFulfillmentPaginatedSerializer,
    RequisicaoRefuseInputSerializer,
)
from apps.requisitions.services import (
    ItemAutorizacaoData,
    ItemRascunhoData,
    atender_requisicao,
    atualizar_rascunho_requisicao,
    autorizar_requisicao,
    cancelar_requisicao,
    criar_rascunho_requisicao,
    descartar_rascunho_nunca_enviado,
    enviar_para_autorizacao,
    listar_fila_atendimento,
    listar_fila_autorizacao,
    recusar_requisicao,
    retornar_para_rascunho,
)

User = get_user_model()


class RequisicaoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RequisicaoDetailOutputSerializer
    filterset_class = RequisicaoFilter
    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    search_fields = [
        "numero_publico",
        "beneficiario__nome_completo",
        "criador__nome_completo",
    ]

    def get_queryset(self):
        if self.action == "list":
            return (
                queryset_requisicoes_visiveis(
                    self.request.user,
                    skip_prefetch=True,
                )
                .annotate(total_itens=Count("itens"))
                .order_by("-updated_at", "-id")
            )
        return queryset_requisicoes_visiveis(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return RequisicaoListOutputSerializer
        return RequisicaoDetailOutputSerializer

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @extend_schema(
        operation_id="requisitions_list",
        tags=["requisitions"],
        description=(
            "Lista paginada das requisições visíveis ao usuário autenticado. "
            "Suporta busca textual simples e filtro por status."
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
            OpenApiParameter(
                name="search",
                description="Busca textual por número público, nome do beneficiário ou nome do criador.",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="status",
                description="Filtro exato por status da requisição.",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: RequisicaoListPaginatedSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        operation_id="requisitions_retrieve",
        tags=["requisitions"],
        description=(
            "Detalhe canônico de uma requisição visível ao usuário autenticado, "
            "incluindo itens e resumo operacional da timeline."
        ),
        responses={
            200: RequisicaoDetailOutputSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        operation_id="requisitions_create_draft",
        tags=["requisitions"],
        request=RequisicaoCreateInputSerializer,
        responses={
            201: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = RequisicaoCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        beneficiario = get_object_or_404(
            User.objects.select_related("setor"), pk=serializer.validated_data["beneficiario_id"]
        )
        requisicao = criar_rascunho_requisicao(
            criador=request.user,
            beneficiario=beneficiario,
            observacao=serializer.validated_data["observacao"],
            itens=[
                ItemRascunhoData(**item_data) for item_data in serializer.validated_data["itens"]
            ],
        )
        output = RequisicaoDetailOutputSerializer(requisicao)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="requisitions_update_draft",
        tags=["requisitions"],
        request=RequisicaoCreateInputSerializer,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["put"], url_path="draft")
    def update_draft(self, request, pk=None):
        serializer = RequisicaoCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            requisicao_id = int(pk)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"pk": ["Identificador de requisição inválido."]}) from exc

        requisicao = atualizar_rascunho_requisicao(
            requisicao_id=requisicao_id,
            ator=request.user,
            beneficiario_id=serializer.validated_data["beneficiario_id"],
            observacao=serializer.validated_data["observacao"],
            itens=[
                ItemRascunhoData(**item_data) for item_data in serializer.validated_data["itens"]
            ],
        )
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_submit",
        tags=["requisitions"],
        request=None,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        requisicao = enviar_para_autorizacao(requisicao=self.get_object(), ator=request.user)
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_return_to_draft",
        tags=["requisitions"],
        request=None,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="return-to-draft")
    def return_to_draft(self, request, pk=None):
        requisicao = retornar_para_rascunho(requisicao=self.get_object(), ator=request.user)
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_discard",
        tags=["requisitions"],
        request=None,
        responses={
            204: None,
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["delete"], url_path="discard")
    def discard(self, request, pk=None):
        descartar_rascunho_nunca_enviado(requisicao=self.get_object(), ator=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="requisitions_cancel",
        tags=["requisitions"],
        request=RequisicaoCancelInputSerializer,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        serializer = RequisicaoCancelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisicao = cancelar_requisicao(
            requisicao=self.get_object(),
            ator=request.user,
            motivo_cancelamento=serializer.validated_data["motivo_cancelamento"],
        )
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_authorize",
        tags=["requisitions"],
        request=RequisicaoAuthorizeInputSerializer,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="authorize")
    def authorize(self, request, pk=None):
        serializer = RequisicaoAuthorizeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisicao = autorizar_requisicao(
            requisicao=self.get_object(),
            ator=request.user,
            itens=[
                ItemAutorizacaoData(**item_data) for item_data in serializer.validated_data["itens"]
            ],
        )
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_refuse",
        tags=["requisitions"],
        request=RequisicaoRefuseInputSerializer,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="refuse")
    def refuse(self, request, pk=None):
        serializer = RequisicaoRefuseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisicao = recusar_requisicao(
            requisicao=self.get_object(),
            ator=request.user,
            motivo_recusa=serializer.validated_data["motivo_recusa"],
        )
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_fulfill",
        tags=["requisitions"],
        request=RequisicaoFulfillInputSerializer,
        responses={
            200: RequisicaoDetailOutputSerializer(),
            400: ErrorResponseSerializer(),
            403: ErrorResponseSerializer(),
            404: ErrorResponseSerializer(),
            409: ErrorResponseSerializer(),
        },
    )
    @action(detail=True, methods=["post"], url_path="fulfill")
    def fulfill(self, request, pk=None):
        serializer = RequisicaoFulfillInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisicao = atender_requisicao(
            requisicao=self.get_object(),
            ator=request.user,
            itens=serializer.validated_data.get("itens"),
            retirante_fisico=serializer.validated_data["retirante_fisico"],
            observacao_atendimento=serializer.validated_data["observacao_atendimento"],
        )
        return Response(RequisicaoDetailOutputSerializer(requisicao).data)

    @extend_schema(
        operation_id="requisitions_pending_approvals",
        tags=["requisitions"],
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
            200: RequisicaoPendingApprovalPaginatedSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        queryset = listar_fila_autorizacao(ator=request.user).annotate(total_itens=Count("itens"))
        page = self.paginate_queryset(queryset)
        serializer = RequisicaoPendingApprovalOutputSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        operation_id="requisitions_pending_fulfillments",
        tags=["requisitions"],
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
            200: RequisicaoPendingFulfillmentPaginatedSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    @action(detail=False, methods=["get"], url_path="pending-fulfillments")
    def pending_fulfillments(self, request):
        queryset = listar_fila_atendimento(ator=request.user).annotate(total_itens=Count("itens"))
        page = self.paginate_queryset(queryset)
        serializer = RequisicaoPendingFulfillmentOutputSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
