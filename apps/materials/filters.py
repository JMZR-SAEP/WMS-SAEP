import django_filters
from django_filters import FilterSet

from apps.materials.models import Material


class MaterialFilter(FilterSet):
    grupo = django_filters.CharFilter(
        field_name="subgrupo__grupo__codigo_grupo",
        lookup_expr="exact",
        help_text="Filtrar por código do grupo (ex: 001)",
    )
    subgrupo = django_filters.CharFilter(
        field_name="subgrupo__codigo_subgrupo",
        lookup_expr="exact",
        help_text="Filtrar por código do subgrupo (ex: 001)",
    )

    class Meta:
        model = Material
        fields = []
