# Project Status — Post-Materialization

**Date:** 2026-05-02
**Status:** Django materialization COMPLETE; PIL-BE-ACE foundation COMPLETE through `PIL-BE-ACE-005`; PIL-BE-MAT-001 COMPLETE; PIL-BE-MAT-002 COMPLETE; PIL-BE-EST-001 COMPLETE; PIL-BE-MAT-003 COMPLETE; PIL-BE-IMP-001 COMPLETE; PIL-BE-IMP-002 COMPLETE; PIL-BE-REQ-001 COMPLETE; `PIL-BE-REQ-002/003/004/005/007/008` COMPLETE; `PIL-BE-AUT-001/003/004/005/006` COMPLETE; `PIL-BE-ATE-001/003/004/005/006` COMPLETE; `PIL-BE-AUD-001/003` COMPLETE; `PIL-BE-NOT-001/002` COMPLETE on branch `feat/notificacoes-fluxo`.
**Current branch context:** repo currently being operated from `main`; this session produced architecture/docs/backlog/planning changes for the pilot frontend plus Serena-memory sync work. Notification-flow branch notes are historical context only.

## Current Baseline

The separate materialization backlog was removed after completion.

Functional foundation complete:
- `apps/users/`: custom user by `matricula_funcional`, setores, papéis, centralized policies, and third-party request creation support from `PIL-BE-ACE-005`
- `apps/materials/`: `GrupoMaterial`, `SubgrupoMaterial`, `Material`, material list/search API, SCPI CSV parser, and import orchestration services
- `apps/stock/`: `EstoqueMaterial`, immutable `MovimentacaoEstoque`, initial-balance registration service, reservation movement on requisition authorization, fulfillment stock exit movement, and reserve-release movement for undelivered partial-fulfillment quantities
- `apps/core/`: DRF/OpenAPI infrastructure, pagination, standard error envelope, and in-process post-commit event pub/sub in `apps/core/events.py`
- `apps/requisitions/`: draft creation, submit/return/discard/cancel before authorization, pending-approvals queue, authorize/refuse actions, pending-fulfillments queue, full and partial fulfillment actions through the unified `atender_requisicao()` service entry point, declarative transition applier, timeline events, authorization reservation side effect, fulfillment stock exit side effect, reserve-release side effect for undelivered partial-fulfillment quantities, and post-commit notification event publication
- `apps/notifications/`: `Notificacao` model, individual or role-targeted notifications, read/unread state for individual notifications, admin scoped by user/papel, and handlers for requisition submit/authorize/refuse/cancel/fulfill events

Technical baseline:
- Django 6.0.4 + DRF + drf-spectacular + django-filter
- PostgreSQL via `DATABASE_URL`
- Ephemeral local migrations; not committed as normal deliverables
- `rtk make init` / `rtk make setup` as primary local workflow
- CI covers lint + Django check + pytest

## Important Invariants Already Landed

- Login by unique `matricula_funcional`
- Inactive user cannot authenticate
- Sector must have a chief; a chief cannot manage two sectors
- Chief-of-sector scope depends on `setor_responsavel`
- Chief of warehouse authorizes only the canonical Almoxarifado sector
- SCPI-backed catalog fields are read-only in normal admin/operational flows
- Material search API returns only active materials and exposes `saldo_disponivel`
- `saldo_disponivel = saldo_fisico - saldo_reservado`
- Initial SCPI stock load creates immutable `SALDO_INICIAL` stock movements
- `MovimentacaoEstoque` remains immutable; `bulk_update`, queryset `update/delete`, instance `save` overwrite, and now `bulk_create` bypasses are blocked or validated through model invariants
- `RESERVA_POR_AUTORIZACAO`, `SAIDA_POR_ATENDIMENTO`, and `LIBERACAO_RESERVA_ATENDIMENTO` are the current operational stock movements and must keep `requisicao`, `item_requisicao`, and `material` coherent through `clean()/full_clean()` plus ORM regression coverage
- Reservation write path rejects `quantidade <= 0` and revalidates `quantidade <= saldo_disponivel` under lock in the stock service itself
- Fulfillment stock exit rejects `quantidade <= 0`, revalidates both `saldo_fisico` and `saldo_reservado` under lock, decrements both balances, and records immutable `SAIDA_POR_ATENDIMENTO`
- Partial-fulfillment reserve release rejects `quantidade <= 0`, requires an active transaction when using `estoque_travado`, validates that the resulting reserved balance does not exceed physical balance, decrements only `saldo_reservado`, and records immutable `LIBERACAO_RESERVA_ATENDIMENTO`
- Requisition public numbers start only on first submission for authorization, never on draft creation
- Requisition public numbering is annual and concurrency-safe
- A returned-to-draft requisition keeps its existing `numero_publico`
- Pending-approvals listing must contain only `aguardando_autorizacao` requests in the caller scope
- Authorization/recusal permission checks run in services against the `select_for_update()`-locked requisition, not against a stale caller instance
- Partial or zero authorization requires non-blank trimmed justification; authorization payload cannot repeat `item_id`; at least one authorized item must remain with quantity greater than zero
- Authorization persists `quantidade_autorizada`, records `AUTORIZACAO_TOTAL` or `AUTORIZACAO_PARCIAL`, and reserves stock without changing `saldo_fisico`
- Refusal requires non-blank trimmed `motivo_recusa`, records `RECUSA`, and must not reserve stock
- Pending-fulfillments listing is global for Almoxarifado roles: `matriz-permissoes.md` says Almoxarifado sees requests from all sectors and the fulfillment queue
- Full fulfillment transitions `autorizada` to `atendida`, sets `quantidade_entregue = quantidade_autorizada` for positive authorized items, records `ATENDIMENTO`, consumes reservation, decrements physical stock, and stores `responsavel_atendimento`, `data_finalizacao`, `retirante_fisico`, and `observacao_atendimento`
- Partial fulfillment transitions `autorizada` to `atendida_parcialmente`, requires all authorized items in the payload, requires at least one item delivered with quantity greater than zero, requires justification for each item delivered below authorized quantity, records `ATENDIMENTO_PARCIAL`, consumes/decrements delivered quantities, and releases reservations for undelivered quantities
- Fulfillment payload-shape/coherence problems are `400 validation_error`; domain-rule failures such as all quantities zero or quantity above authorized remain `409 domain_conflict`
- Fulfillment permission checks run in services against the `select_for_update()`-locked requisition via object-aware policy `pode_atender_requisicao`
- Pre-authorization discard is physical only for never-formalized drafts; pre-authorization cancel is logical

## Current Validation Snapshot

- `rtk make test` passed locally on 2026-04-29 with 175 collected tests before the requisition workflow slice landed
- For the merged requisitions slice, the validated local flow remains `rtk make init` then `rtk make setup` before pytest when schema/model changes are involved
- After the authorization hardening follow-up merged in PR #24, targeted local validation passed with:
  - `rtk pytest tests/requisitions/test_services.py tests/stock/test_services_estoque.py`
  - `rtk ruff check apps/requisitions/services.py apps/stock/models.py apps/stock/services.py tests/requisitions/test_services.py tests/stock/test_services_estoque.py`
- After the fulfillment PR #25 merged, targeted local validation passed with:
  - `rtk pytest tests/requisitions/test_api.py tests/requisitions/test_services.py tests/stock/test_services_estoque.py`
  - `rtk pytest tests/test_api_schema.py::TestOpenAPISchema::test_schema_contem_rotas_de_requisicoes`
  - `rtk ruff check` for touched requisitions/stock files
- The repository now contains API, service, stock, PostgreSQL-concurrency, and OpenAPI tests covering the delivered requisition authorization, full-fulfillment, and partial-fulfillment endpoints and invariants
- PR #26 local validation passed after review fixes with `rtk make test` collecting 292 tests; focused requisitions/stock validation passed with `rtk proxy pytest tests/stock/test_services_estoque.py tests/requisitions/test_services.py tests/requisitions/test_api.py -q` collecting 84 tests
- PR #28 notification flow validation on branch `feat/notificacoes-fluxo` passed with `rtk make setup`, focused Ruff, focused notifications/admin tests, and final `rtk make test` collecting 320 tests after review hardening

## Recommended Next PR Sequence

1. `#31` / bloco 0 de autenticação e sessão para SPA
   - deliver `csrf`, `login`, `logout`, and `me` for session-based SPA auth
2. bloco 0 restante, nesta ordem já aprovada na sessão:
   - lookup de beneficiário por nome
   - leituras canônicas de requisição (`GET /requisitions/` e `GET /requisitions/{id}/`)
   - atualização explícita de rascunho por substituição completa
3. depois do bloco 0:
   - login/bootstrap da SPA
   - CI inicial do frontend
   - `Minhas requisições`
   - criação/edição de rascunho e envio
   - filas de autorizações e atendimento
4. depois disso:
   - Playwright/CI fase 2
   - notificações da SPA como segunda onda

GitHub issue planning created in this session:
- issues `#31` through `#44` were opened as vertical slices for the frontend pilot and supporting work
- `#31` (`Frontend piloto: bloco 0 de autenticação e sessão para SPA`) is already labeled `ready-for-agent`

Post-pilot/MVP technical follow-up:
- Individual read state for role-targeted notifications remains deferred. Current role notifications are visible by admin scope but cannot be individually marked as read because `Notificacao.lida/lida_em` is global to the notification row.
- Return / estorno / exceptional stock-exit flows remain later MVP work and must reuse the canonical requisition/item/stock lock order before adding new stock writers.

## Notes For Future Agents

- Prefer backend/API-first slices, but note that frontend pilot work is now active scope after the macro SPA decision; do not start operational SPA implementation before bloco 0 is done
- The SPA scaffold already exists in `frontend/`; evolve it incrementally instead of recreating project setup or route foundations.
- Reuse `apps/users/policies.py` from both services and views
- Keep business rules in services/use cases, not in views/serializers/admin
- Treat SCPI import as a service pipeline: parser/normalization + domain creation + stock initialization, with atomic persistence
- For anything involving stock mutation, preserve the documented transaction/locking posture and define canonical lock order before adding more stock writer flows
- In this repo phase, DB-level trigger/migration enforcement for some stock invariants may still be deferred; when that happens, document the residual risk explicitly and keep ORM-level guards/tests aligned with the decision
