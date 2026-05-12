from apps.analytics.models import FrontendAnalyticsEvent
from apps.users.models import User


def registrar_frontend_analytics_event(
    *,
    usuario: User,
    event_type: str,
    screen: str = "",
    draft_step: str = "",
    action: str = "",
    endpoint_key: str = "",
    http_status: int | None = None,
    error_code: str = "",
    trace_id: str = "",
) -> FrontendAnalyticsEvent:
    return FrontendAnalyticsEvent.objects.create(
        usuario=usuario,
        papel=usuario.papel,
        event_type=event_type,
        screen=screen,
        draft_step=draft_step,
        action=action,
        endpoint_key=endpoint_key,
        http_status=http_status,
        error_code=error_code,
        trace_id=trace_id,
    )
