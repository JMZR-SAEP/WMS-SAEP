from django.contrib import admin

from apps.notifications.models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo",
        "destinatario",
        "papel_destinatario",
        "lida",
        "created_at",
    )
    list_filter = ("tipo", "lida", "papel_destinatario", "created_at")
    search_fields = (
        "titulo",
        "mensagem",
        "destinatario__matricula_funcional",
        "destinatario__nome_completo",
    )
    readonly_fields = ("created_at",)
