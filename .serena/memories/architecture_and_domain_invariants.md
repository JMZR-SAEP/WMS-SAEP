# Architecture and domain invariants

Core architectural rule: business rules belong in `services.py` / service-use-case modules. Keep DRF views, serializers, templates, admin actions, signals, management commands, and generic helpers thin. Serializers validate input/output shape and local payload coherence, not critical domain workflow.

Authorization must be explicit and consistent. Contextual authorization should be centralized in `policies.py` or equivalent and used by both views and services. Always validate object scope/profile in services for writes.

Every API endpoint must follow `docs/design-acesso-rapido/api-contracts.md`: session authentication with CSRF by default, general authorization through `permission_classes`, contextual authorization through shared policies, explicit input/output serializers, explicit status codes, the standard error envelope, pagination/filtering/ordering when applicable, and OpenAPI schema coverage. Changes to API contracts require tests and schema updates.

API response invariant:
- Successful detail/action responses return the resource or result directly, without a global success envelope.
- List responses use the standard pagination envelope with `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, and `results`.
- Error responses always use `{ "error": { "code", "message", "details", "trace_id" } }`.
- Error codes are stable English machine codes; messages are PT-BR.
- Domain conflicts use HTTP 409 with code `domain_conflict`.

Stock invariants:
- `StockMovement` is immutable. Do not update/delete/overwrite movements; corrections are new `RETURN` movements.
- Any operation altering stock uses `transaction.atomic()` and row locking such as `select_for_update()` on `Stock`.
- Keep `Stock.quantity` and `StockMovement.balance_after` consistent.
- Avoid double decrement, unauthorized negative stock, race conditions, and movement/balance divergence.

Request/requisition invariants:
- `MaterialRequest.department` is a historical snapshot and must not be recalculated from `requester.department` after creation.
- Request status transitions must follow the declarative state machine documented in domain/process docs and existing services when present.
- Do not scatter status transitions through ad hoc `if/elif` logic.
- Preserve consistency between request, request items, deliveries, delivery items, stock reservation, and stock decrement.

Notifications:
- Notifications are side effects, never source of truth and never precondition for domain success.
- Domain apps communicate with notifications via `core/events.py` in-process pub/sub: `subscribe()` and `publish_on_commit()`.
- Avoid direct imports from domain apps into `notifications` that create coupling.

Audit/rastreability:
- Relevant actions must be auditable: creation, approval, rejection, return to draft, cancellation, delivery, adjustment, reversal.
- Audit/history is expected through `django-simple-history` (`HistoricalRecords`) for domain models, not manual logging/signals.

Dependency direction:
`apps/core/` is technical infrastructure only and must not depend on domain apps. Domain app dependencies should remain explicit and acyclic as apps are introduced by the backlog. Notifications and other side effects must be reached by post-commit events instead of direct domain coupling.

Development environment rule: local DB and app migrations are ephemeral during this early phase. Do not commit generated app migrations. For schema/model changes, rebuild local migrations and validate against a clean local database. Generated migrations are temporary materialization artifacts, not normal deliverables.