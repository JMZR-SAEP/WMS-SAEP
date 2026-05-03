import django_filters
from django_filters import FilterSet

from apps.requisitions.models import Requisicao


class RequisicaoFilter(FilterSet):
    status = django_filters.CharFilter(
        field_name="status",
        lookup_expr="exact",
        help_text="Filtrar por status da requisição.",
    )

    class Meta:
        model = Requisicao
        fields = []
