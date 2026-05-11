from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.notifications.models import Notificacao, PushSubscription

REQUISICAO_APP_LABEL = "requisitions"
REQUISICAO_MODEL = "requisicao"


class NotificacaoDestinoOutputSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=["usuario", "papel"], read_only=True)
    usuario_id = serializers.IntegerField(required=False, allow_null=True, read_only=True)
    papel = serializers.CharField(required=False, allow_null=True, read_only=True)


class NotificacaoObjetoRelacionadoOutputSerializer(serializers.Serializer):
    tipo = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    numero_publico = serializers.CharField(required=False, allow_null=True, read_only=True)
    status = serializers.CharField(required=False, read_only=True)


class NotificacaoOutputSerializer(serializers.ModelSerializer):
    leitura_suportada = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    objeto_relacionado = serializers.SerializerMethodField()

    class Meta:
        model = Notificacao
        fields = [
            "id",
            "tipo",
            "titulo",
            "mensagem",
            "created_at",
            "lida",
            "lida_em",
            "leitura_suportada",
            "destino",
            "objeto_relacionado",
        ]
        read_only_fields = fields

    def get_leitura_suportada(self, obj: Notificacao) -> bool:
        return obj.destinatario_id is not None

    @extend_schema_field(NotificacaoDestinoOutputSerializer)
    def get_destino(self, obj: Notificacao) -> dict[str, object]:
        if obj.destinatario_id is not None:
            return {
                "tipo": "usuario",
                "usuario_id": obj.destinatario_id,
                "papel": None,
            }

        return {
            "tipo": "papel",
            "usuario_id": None,
            "papel": obj.papel_destinatario,
        }

    @extend_schema_field(NotificacaoObjetoRelacionadoOutputSerializer(allow_null=True))
    def get_objeto_relacionado(self, obj: Notificacao) -> dict[str, object] | None:
        if obj.content_type_id is None or obj.object_id is None:
            return None

        if (
            obj.content_type.app_label != REQUISICAO_APP_LABEL
            or obj.content_type.model != REQUISICAO_MODEL
        ):
            return None

        requisicao = obj.objeto_relacionado
        if requisicao is None:
            return {
                "tipo": "requisicao",
                "id": obj.object_id,
            }

        return {
            "tipo": "requisicao",
            "id": requisicao.id,
            "numero_publico": requisicao.numero_publico,
            "status": requisicao.status,
        }


class NotificacaoListPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.URLField(allow_null=True, read_only=True)
    previous = serializers.URLField(allow_null=True, read_only=True)
    results = NotificacaoOutputSerializer(many=True, read_only=True)


class NotificacaoUnreadCountOutputSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(read_only=True)


class PushConfigOutputSerializer(serializers.Serializer):
    enabled = serializers.BooleanField(read_only=True)
    vapid_public_key = serializers.CharField(allow_blank=True, read_only=True)


class PushSubscriptionKeysInputSerializer(serializers.Serializer):
    p256dh = serializers.CharField()
    auth = serializers.CharField()


class PushSubscriptionInputSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    keys = PushSubscriptionKeysInputSerializer()


class PushSubscriptionOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["endpoint", "active"]
        read_only_fields = fields


class PushSubscriptionDeactivateInputSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
