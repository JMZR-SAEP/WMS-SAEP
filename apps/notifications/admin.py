from django.contrib import admin, messages
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import Notificacao
from apps.notifications.services import marcar_notificacao_como_lida


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    actions = ("marcar_como_lida_action",)
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
    readonly_fields = ("created_at", "lida", "lida_em")
    list_select_related = ("destinatario",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(
            Q(destinatario=request.user) | Q(papel_destinatario=request.user.papel)
        )

    @admin.action(description="Marcar notificações selecionadas como lidas")
    def marcar_como_lida_action(self, request, queryset):
        marcadas = 0
        recusadas = 0
        ultima_mensagem_erro = ""

        for notificacao in queryset:
            try:
                marcar_notificacao_como_lida(notificacao=notificacao, usuario=request.user)
            except PermissionDenied as exc:
                recusadas += 1
                ultima_mensagem_erro = str(exc.detail)
                continue
            marcadas += 1

        if marcadas:
            self.message_user(
                request,
                f"{marcadas} notificação(ões) marcada(s) como lida(s).",
                level=messages.SUCCESS,
            )
        if recusadas:
            self.message_user(
                request,
                (
                    f"{recusadas} notificação(ões) não foram marcadas como lidas. "
                    f"{ultima_mensagem_erro}"
                ),
                level=messages.WARNING,
            )
