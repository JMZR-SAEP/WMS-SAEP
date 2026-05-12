from django.contrib import admin

from apps.analytics.models import FrontendAnalyticsEvent


@admin.register(FrontendAnalyticsEvent)
class FrontendAnalyticsEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "papel",
        "event_type",
        "screen",
        "draft_step",
        "http_status",
        "created_at",
    )
    list_filter = ("event_type", "screen", "draft_step", "papel", "http_status", "created_at")
    search_fields = ("usuario__matricula_funcional", "usuario__nome_completo", "trace_id")
    readonly_fields = (
        "usuario",
        "papel",
        "event_type",
        "screen",
        "draft_step",
        "action",
        "endpoint_key",
        "http_status",
        "error_code",
        "trace_id",
        "created_at",
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
