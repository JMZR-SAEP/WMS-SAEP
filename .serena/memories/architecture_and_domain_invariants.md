# Architecture and domain invariants

Core architectural rule: business rules belong in `services.py` / service-use-case modules. Keep DRF views, serializers, templates, admin actions, signals, management commands, and generic helpers thin. Serializers validate input/output shape and local payload coherence, not critical domain workflow.

Authorization must be explicit and consistent. Contextual authorization should be centralized in `policies.py` or equivalent and used by both views and services. Always validate object scope/profile in services for writes, and for concurrent write paths prefer validating against the locked/reloaded object inside `transaction.atomic()` instead of the potentially stale caller instance.

Authentication invariant:
- The pilot login identifier is `matricula_funcional`.
- Custom Django auth backends must stay compatible with the standard `authenticate(username=..., password=...)` flow in addition to `USERNAME_FIELD`/explicit credential kwargs, so Django Admin, forms, and session-based flows keep working.
- Missing-user authentication paths should still execute password hashing work before returning `None` to reduce timing-based user enumeration.

Every API endpoint must follow `docs/design-acesso-rapido/api-contracts.md`: session authentication with CSRF by default, general authorization through `permission_classes`, contextual authorization through shared policies, explicit input/output serializers, explicit status codes, the standard error envelope, pagination/filtering/ordering when applicable, and OpenAPI schema coverage. Changes to API contracts require tests and schema updates.

API response invariant:
- Successful detail/action responses return the resource or result directly, without a global success envelope.
- List responses use the standard pagination envelope with `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, and `results`.
- Error responses always use `{ "error": { "code", "message", "details", "trace_id" } }`.
- Error codes are stable English machine codes; messages are PT-BR.
- Domain conflicts use HTTP 409 with code `domain_conflict`.

Stock invariants:
- `MovimentacaoEstoque` is immutable. Do not update/delete/overwrite movements; corrections must be modeled as new movements when new movement types are introduced.
- The currently implemented movement types are `SALDO_INICIAL` for SCPI bootstrap load, `RESERVA_POR_AUTORIZACAO` for approved requisition reservation, `SAIDA_POR_ATENDIMENTO` for delivered fulfillment quantities, and `LIBERACAO_RESERVA_ATENDIMENTO` for authorized quantities not delivered during partial fulfillment.
- Any operation altering stock uses `transaction.atomic()` and row locking such as `select_for_update()` on stock rows.
- Keep `EstoqueMaterial.saldo_fisico`, `saldo_reservado`, `saldo_disponivel`, and movement balances consistent.
- Avoid double increment/decrement, unauthorized negative stock, race conditions, and movement/balance divergence.
- The stock reservation write path must reject `quantidade <= 0` and must revalidate available balance inside the locked stock service itself, even if the caller already checked before.
- The fulfillment stock exit write path must reject `quantidade <= 0`, revalidate both `saldo_fisico` and `saldo_reservado` after locking stock, decrement both balances, and record immutable `SAIDA_POR_ATENDIMENTO`.
- The fulfillment reserve-release write path must reject `quantidade <= 0`, revalidate reserved balance under an active transaction, preserve `saldo_fisico`, prevent `saldo_fisico < saldo_reservado_posterior`, decrement only `saldo_reservado`, and record immutable `LIBERACAO_RESERVA_ATENDIMENTO`.
- Stock service shortcuts that receive an already locked `EstoqueMaterial` through `estoque_travado` must only run inside an active `transaction.atomic()` block; callers outside an orchestrating transaction must let the stock service acquire the lock itself.
- `MovimentacaoEstoque.save()` calls `full_clean()`, and manager-level bulk paths must not bypass critical invariants; `bulk_create()` is now expected to validate each object before insert.
- Current cross-field consistency between `requisicao`, `item_requisicao`, and `material` for operational stock movements is enforced at the ORM/model level with `clean()/full_clean()` plus regression tests; if durable DB-level enforcement becomes required later, add it explicitly and document the migration decision.

Technical debt to revisit before adding new stock writers:
- PR #26 established the current fulfillment lock order: lock `Requisicao`, then authorized `ItemRequisicao` rows ordered by `material_id, id`, then all related `EstoqueMaterial` rows in deterministic `material_id` order before calling stock writers with `estoque_travado`. Future flows such as exceptional exits, reversals, returns, or cancellation release must reuse a canonical lock order and add PostgreSQL concurrency coverage rather than introducing a parallel sequence.

Request/requisition invariants:
- `Requisicao.setor_beneficiario` is a historical snapshot and must not be recalculated from `beneficiario.setor` after creation.
- Request status transitions must follow the declarative state machine documented in domain/process docs and existing services when present.
- Do not scatter status transitions through ad hoc `if/elif` logic.
- Preserve consistency between requisition, requisition items, stock reservation, stock decrement, delivery, and audit trail.
- Authorization rules are service-level domain rules, not serializer-only rules: payload-level guards in DRF are welcome, but critical checks must also exist in `apps/requisitions/services.py`.
- Authorization payload must not repeat `item_id`.
- Partial or zero authorization requires a non-blank trimmed justification.
- At least one item must remain with `quantidade_autorizada > 0` for an authorization to succeed.
- Authorization records either `AUTORIZACAO_TOTAL` or `AUTORIZACAO_PARCIAL`, persists authorized quantities on items, and reserves stock without changing physical balance.
- Refusal requires non-blank trimmed `motivo_recusa`, records `RECUSA`, and must not reserve stock.
- The fulfillment queue is global for Almoxarifado roles by design: `docs/design-acesso-rapido/matriz-permissoes.md` says Almoxarifado sees requests from all sectors and the fulfillment queue.
- Full fulfillment transitions `autorizada` to `atendida`, sets delivered quantity equal to authorized quantity for positive authorized items, records `ATENDIMENTO`, consumes reservation, decrements physical stock, and stores fulfillment metadata.
- Partial fulfillment transitions `autorizada` to `atendida_parcialmente`, requires the payload to cover every authorized item exactly once, requires a non-blank justification for every item delivered below the authorized quantity including zero, requires at least one delivered quantity greater than zero, records `ATENDIMENTO_PARCIAL`, decrements stock only for delivered quantities, and releases the reservation for undelivered quantities.
- Fulfillment payload coherence errors such as duplicated, unknown, or omitted `item_id` are `ValidationError` / HTTP `400 validation_error`; domain state/rule conflicts such as all delivered quantities equal to zero, delivery above authorized quantity, insufficient physical/reserved stock, or invalid status remain `409 domain_conflict`.
- Fulfillment writes must revalidate object-aware permission in services against the `select_for_update()`-locked requisition through `pode_atender_requisicao`; global role checks alone are insufficient for writes.

Notifications:
- Notifications are side effects, never source of truth and never precondition for domain success.
- Domain apps communicate with notifications via `core/events.py` in-process pub/sub: `subscribe()` and `publish_on_commit()`.
- Avoid direct imports from domain apps into `notifications` that create coupling.

Audit/rastreability:
- Relevant actions must be auditable: creation, approval, rejection, return to draft, cancellation, delivery, adjustment, reversal.
- Audit/history is expected through `django-simple-history` (`HistoricalRecords`) for domain models, not manual logging/signals.

Dependency direction:
`apps/core/` is technical infrastructure only and must not depend on domain apps. Domain app dependencies should remain explicit and acyclic as apps are introduced by the backlog. Notifications and other side effects must be reached by post-commit events instead of direct domain coupling.

Materials/SCPI invariants:
- `GrupoMaterial` and `SubgrupoMaterial` are structural catalogs backed by SCPI data, not freeform WMS-maintained master data.
- SCPI code fragments for group/subgroup must remain exactly 3 numeric digits and should be enforced both in model validation and with DB-level constraints.
- Manual operational mutation of SCPI-official fields such as group/subgroup codes and names should not be exposed through normal admin add/change/delete surfaces.
- Material search/list selection for requisition flows must return only active materials and include current `saldo_disponivel`.
- The SCPI import pipeline is parser/normalizer first, service orchestration second, persistence third; do not collapse critical normalization into ad hoc command logic.
- SCPI CSV parsing must tolerate UTF-8 BOM, semicolon-separated input, logical records with multiline continuation, and quantity normalization such as decimal comma.
- SCPI import persistence is all-or-nothing: parsing, material creation, stock creation, and initial-balance movement registration must commit atomically.
- Imported material names should be normalized to a single line / single-space representation before persistence.

Development environment rule: local DB and app migrations are ephemeral during this early phase. Do not commit generated app migrations. For schema/model changes, rebuild local migrations and validate against a clean local database. Generated migrations are temporary materialization artifacts, not normal deliverables.
