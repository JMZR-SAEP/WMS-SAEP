# PR 28 notifications technical debt

Context: branch `feat/notificacoes-fluxo`, PR #28, commits through `020ad4d`.

Consolidated debt / follow-up:
- Role-targeted notifications (`papel_destinatario`) are currently global rows. They are visible to staff users with the matching role through `NotificacaoAdmin.get_queryset()`, but they cannot be marked as read by an individual user because `Notificacao.lida/lida_em` belongs to the shared notification row.
- `marcar_notificacao_como_lida()` therefore rejects notifications with `destinatario_id is None` via DRF `PermissionDenied`. Do not loosen this without adding an explicit per-user read/acknowledgement model or equivalent API contract.
- Future `PIL-FS-NOT-003`/notification API work should decide whether role-targeted notifications are fanned out into individual `Notificacao` rows at creation time or tracked through a separate join model such as `NotificacaoLeitura(usuario, notificacao, lida_em)`. Until then, counters/list/read APIs must avoid presenting role notifications as individually markable.
- Additional non-blocking test coverage opportunities: inactive recipient path in `criar_notificacao_usuario()`, reenvio para autorizacao notification behavior, and authorization partial notification behavior.
- Optional observability follow-up: enrich notification handler logging for `Requisicao.DoesNotExist` with `requisicao_id`; current `publish()` already catches/logs subscriber failures and protects the domain transaction.

Current invariants after review hardening:
- `NotificacaoAdmin` scopes read access by individual `destinatario` or matching `papel_destinatario`; superuser sees all.
- `NotificacaoAdmin.list_select_related = ("destinatario",)` avoids changelist N+1 for individual recipients.
- Admin action `marcar_como_lida_action` calls the service and surfaces permission failures as admin messages.
- Requisition services publish notification events only inside active transactions before registering `publish_on_commit()`.
- `apps/core/events.clear_subscribers()` exists for tests that monkeypatch subscribers.

Validation snapshot:
- `rtk proxy pytest tests/notifications/test_admin.py tests/notifications/test_notifications.py -q` passed with 15 tests.
- `rtk make test` passed with 320 tests.
