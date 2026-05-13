import re

from rest_framework import serializers

from apps.analytics.models import (
    FrontendAnalyticsDraftStep,
    FrontendAnalyticsEvent,
    FrontendAnalyticsEventType,
    FrontendAnalyticsScreen,
)

SENSITIVE_FIELD_NAMES = {
    "beneficiario",
    "beneficiario_id",
    "content",
    "details",
    "endpoint",
    "id",
    "itens",
    "material",
    "material_id",
    "mensagem",
    "nome",
    "numero",
    "numero_publico",
    "password",
    "raw_url",
    "requisicao",
    "requisicao_id",
    "text",
    "user",
    "user_id",
    "usuario",
    "usuario_id",
}
UUID_ENDPOINT_SEGMENT_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
HEX_ENDPOINT_SEGMENT_RE = re.compile(r"^[0-9a-fA-F]{8,}$")


def _endpoint_segment_has_identifier(segment: str) -> bool:
    return (
        segment.isdigit()
        or bool(UUID_ENDPOINT_SEGMENT_RE.fullmatch(segment))
        or bool(HEX_ENDPOINT_SEGMENT_RE.fullmatch(segment))
    )


class FrontendAnalyticsEventInputSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=FrontendAnalyticsEventType.choices)
    screen = serializers.ChoiceField(
        choices=FrontendAnalyticsScreen.choices,
        required=False,
        allow_blank=True,
    )
    draft_step = serializers.ChoiceField(
        choices=FrontendAnalyticsDraftStep.choices,
        required=False,
        allow_blank=True,
    )
    action = serializers.CharField(required=False, allow_blank=True, max_length=60)
    endpoint_key = serializers.RegexField(
        regex=r"^[a-z0-9_:/{}.-]+$",
        required=False,
        allow_blank=True,
        max_length=120,
    )
    http_status = serializers.IntegerField(required=False, min_value=100, max_value=599)
    error_code = serializers.RegexField(
        regex=r"^[a-z0-9_.-]+$",
        required=False,
        allow_blank=True,
        max_length=80,
    )
    trace_id = serializers.RegexField(
        regex=r"^[A-Za-z0-9_.:-]+$",
        required=False,
        allow_blank=True,
        max_length=120,
    )

    def validate(self, attrs):
        extra_fields = set(getattr(self, "initial_data", {})) - set(self.fields)
        sensitive_fields = sorted(extra_fields & SENSITIVE_FIELD_NAMES)
        if extra_fields:
            raise serializers.ValidationError(
                {
                    "non_field_errors": ["Payload de analytics contém campos não permitidos."],
                    "campos_extras": sorted(extra_fields),
                    "campos_sensiveis": sensitive_fields,
                }
            )
        endpoint_key = attrs.get("endpoint_key", "")
        if any(
            _endpoint_segment_has_identifier(segment)
            for segment in endpoint_key.strip("/").split("/")
        ):
            raise serializers.ValidationError(
                {
                    "endpoint_key": [
                        "Use uma chave normalizada, sem identificadores reais no caminho."
                    ]
                }
            )
        return attrs


class FrontendAnalyticsEventOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrontendAnalyticsEvent
        fields = [
            "event_type",
            "screen",
            "draft_step",
            "action",
            "endpoint_key",
            "http_status",
            "error_code",
            "trace_id",
            "created_at",
        ]
        read_only_fields = fields
