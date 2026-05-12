from django.contrib import admin, messages
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.notifications.models import Notificacao, PushClientEvent, PushReminderState
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


@admin.register(PushClientEvent)
class PushClientEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "papel",
        "event_type",
        "diagnostic_status",
        "event_date",
        "updated_at",
    )
    list_filter = ("event_type", "diagnostic_status", "papel", "event_date")
    search_fields = ("usuario__matricula_funcional", "usuario__nome_completo")
    readonly_fields = (
        "usuario",
        "papel",
        "event_type",
        "diagnostic_status",
        "notification_supported",
        "service_worker_supported",
        "push_manager_supported",
        "badging_supported",
        "standalone_display",
        "event_date",
        "created_at",
        "updated_at",
    )
    list_select_related = ("usuario",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(PushReminderState)
class PushReminderStateAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "reminder_type", "last_count", "last_sent_at")
    list_filter = ("reminder_type", "last_sent_at")
    search_fields = ("usuario__matricula_funcional", "usuario__nome_completo")
    readonly_fields = (
        "usuario",
        "reminder_type",
        "last_sent_at",
        "last_count",
        "created_at",
        "updated_at",
    )
    list_select_related = ("usuario",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
