from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.api.serializers import ErrorResponseSerializer
from apps.materials.filters import MaterialFilter
from apps.materials.models import Material
from apps.materials.serializers import (
    MaterialListOutputSerializer,
    MaterialListPaginatedSerializer,
)


class MaterialViewSet(ReadOnlyModelViewSet):
    """API de busca de materiais para seleção em requisições.

    Retorna apenas materiais ativos com saldo disponível calculado.
    Suporta busca textual e filtros estruturados por grupo/subgrupo.
    """

    queryset = (
        Material.objects.filter(is_active=True)
        .select_related("subgrupo__grupo", "estoque")
        .order_by("codigo_completo")
    )
    serializer_class = MaterialListOutputSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = MaterialFilter
    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
    ]
    search_fields = ["codigo_completo", "nome", "descricao"]

    @extend_schema(
        operation_id="materials_list",
        tags=["materials"],
        description="Lista paginada de materiais ativos com saldo disponível calculado. Retorna apenas materiais com is_active=True.",
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
                description="Busca textual em: codigo_completo, nome, descricao (case-insensitive)",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="grupo",
                description="Filtro por código do grupo (ex: 001)",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="subgrupo",
                description="Filtro por código do subgrupo (ex: 001)",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: MaterialListPaginatedSerializer(),
            403: ErrorResponseSerializer(),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
