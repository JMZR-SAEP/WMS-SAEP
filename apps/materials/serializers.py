from decimal import Decimal

from rest_framework import serializers

from apps.materials.models import Material


class MaterialListOutputSerializer(serializers.ModelSerializer):
    """Serializer para listagem de materiais disponíveis.

    Campo saldo_disponivel é calculado dinamicamente (saldo_fisico - saldo_reservado).
    Bloqueios por saldo insuficiente ou divergência crítica são validados na criação da requisição.
    """

    saldo_disponivel = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = [
            "id",
            "codigo_completo",
            "nome",
            "descricao",
            "unidade_medida",
            "saldo_disponivel",
        ]
        read_only_fields = fields

    def get_saldo_disponivel(self, obj) -> Decimal | None:
        """Retorna saldo_disponivel do EstoqueMaterial associado, ou None se não existir."""
        if hasattr(obj, "estoque") and obj.estoque:
            return obj.estoque.saldo_disponivel
        return None
