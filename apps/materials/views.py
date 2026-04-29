from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.materials.filters import MaterialFilter
from apps.materials.models import Material
from apps.materials.serializers import MaterialListOutputSerializer


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
        description="Lista paginada de materiais ativos com saldo disponível.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
