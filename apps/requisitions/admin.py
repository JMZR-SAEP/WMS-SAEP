from django.contrib import admin

from apps.requisitions.models import EventoTimeline, ItemRequisicao, Requisicao


@admin.register(Requisicao)
class RequisicaoAdmin(admin.ModelAdmin):
    list_display = [
        "numero_publico",
        "status",
        "beneficiario",
        "setor_beneficiario",
        "data_criacao",
    ]
    list_filter = ["status", "setor_beneficiario", "data_criacao"]
    search_fields = ["numero_publico", "beneficiario__nome_completo"]
    readonly_fields = [
        "criador",
        "beneficiario",
        "setor_beneficiario",
        "data_criacao",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = [
        "criador",
        "beneficiario",
        "chefe_autorizador",
        "responsavel_atendimento",
    ]
    fieldsets = (
        (
            "Informações básicas",
            {
                "fields": (
                    "numero_publico",
                    "status",
                    "criador",
                    "beneficiario",
                    "setor_beneficiario",
                )
            },
        ),
        (
            "Datas",
            {
                "fields": (
                    "data_criacao",
                    "data_envio_autorizacao",
                    "data_autorizacao_ou_recusa",
                    "data_finalizacao",
                )
            },
        ),
        (
            "Autorização",
            {
                "fields": (
                    "chefe_autorizador",
                    "motivo_recusa",
                )
            },
        ),
        (
            "Atendimento",
            {
                "fields": (
                    "responsavel_atendimento",
                    "retirante_fisico",
                    "motivo_cancelamento",
                )
            },
        ),
        (
            "Observações",
            {"fields": ("observacao",)},
        ),
        (
            "Meta",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ItemRequisicao)
class ItemRequisicaoAdmin(admin.ModelAdmin):
    list_display = [
        "requisicao",
        "material",
        "quantidade_solicitada",
        "quantidade_autorizada",
        "quantidade_entregue",
    ]
    list_filter = ["requisicao__status", "created_at"]
    search_fields = ["requisicao__numero_publico", "material__codigo_completo"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["requisicao", "material"]
    fieldsets = (
        (
            "Informações básicas",
            {
                "fields": (
                    "requisicao",
                    "material",
                    "unidade_medida",
                )
            },
        ),
        (
            "Quantidades",
            {
                "fields": (
                    "quantidade_solicitada",
                    "quantidade_autorizada",
                    "justificativa_autorizacao_parcial",
                    "quantidade_entregue",
                    "justificativa_atendimento_parcial",
                )
            },
        ),
        (
            "Observações",
            {"fields": ("observacao",)},
        ),
        (
            "Meta",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoTimeline)
class EventoTimelineAdmin(admin.ModelAdmin):
    list_display = ["requisicao", "tipo_evento", "usuario", "data_hora"]
    list_filter = ["tipo_evento", "data_hora"]
    search_fields = ["requisicao__numero_publico", "usuario__nome_completo"]
    readonly_fields = ["data_hora"]
    raw_id_fields = ["requisicao", "usuario"]
    fieldsets = (
        (
            "Evento",
            {
                "fields": (
                    "requisicao",
                    "tipo_evento",
                    "usuario",
                    "data_hora",
                )
            },
        ),
        (
            "Detalhes",
            {"fields": ("observacao",)},
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
