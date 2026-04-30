from rest_framework import serializers

from apps.requisitions.models import ItemRequisicao, Requisicao


class RequisicaoUserOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    matricula_funcional = serializers.CharField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)


class RequisicaoSetorOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nome = serializers.CharField(read_only=True)


class RequisicaoMaterialOutputSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    codigo_completo = serializers.CharField(read_only=True)
    nome = serializers.CharField(read_only=True)
    unidade_medida = serializers.CharField(read_only=True)


class RequisicaoItemCreateInputSerializer(serializers.Serializer):
    material_id = serializers.IntegerField()
    quantidade_solicitada = serializers.DecimalField(max_digits=12, decimal_places=3)
    observacao = serializers.CharField(required=False, allow_blank=True, default="")


class RequisicaoCreateInputSerializer(serializers.Serializer):
    beneficiario_id = serializers.IntegerField()
    observacao = serializers.CharField(required=False, allow_blank=True, default="")
    itens = RequisicaoItemCreateInputSerializer(many=True, min_length=1)


class RequisicaoActionOutputSerializer(serializers.ModelSerializer):
    material = RequisicaoMaterialOutputSerializer(read_only=True)

    class Meta:
        model = ItemRequisicao
        fields = [
            "id",
            "material",
            "unidade_medida",
            "quantidade_solicitada",
            "quantidade_autorizada",
            "quantidade_entregue",
            "justificativa_autorizacao_parcial",
            "justificativa_atendimento_parcial",
            "observacao",
        ]
        read_only_fields = fields


class RequisicaoDetailOutputSerializer(serializers.ModelSerializer):
    criador = RequisicaoUserOutputSerializer(read_only=True)
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    itens = RequisicaoActionOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "data_criacao",
            "data_envio_autorizacao",
            "data_autorizacao_ou_recusa",
            "data_finalizacao",
            "observacao",
            "itens",
        ]
        read_only_fields = fields


class RequisicaoPendingApprovalOutputSerializer(serializers.ModelSerializer):
    criador = RequisicaoUserOutputSerializer(read_only=True)
    beneficiario = RequisicaoUserOutputSerializer(read_only=True)
    setor_beneficiario = RequisicaoSetorOutputSerializer(read_only=True)
    total_itens = serializers.IntegerField(read_only=True)

    class Meta:
        model = Requisicao
        fields = [
            "id",
            "numero_publico",
            "status",
            "data_envio_autorizacao",
            "criador",
            "beneficiario",
            "setor_beneficiario",
            "total_itens",
        ]
        read_only_fields = fields


class RequisicaoPendingApprovalPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.URLField(allow_null=True, read_only=True)
    previous = serializers.URLField(allow_null=True, read_only=True)
    results = RequisicaoPendingApprovalOutputSerializer(many=True, read_only=True)
