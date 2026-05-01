# Project Status — Post-Materialization

**Date:** 2026-05-01
**Status:** Django materialization COMPLETE; PIL-BE-ACE foundation COMPLETE through `PIL-BE-ACE-005`; PIL-BE-MAT-001 COMPLETE; PIL-BE-MAT-002 COMPLETE; PIL-BE-EST-001 COMPLETE; PIL-BE-MAT-003 COMPLETE; PIL-BE-IMP-001 COMPLETE; PIL-BE-IMP-002 COMPLETE; PIL-BE-REQ-001 COMPLETE; `PIL-BE-REQ-002/003/004/005/007/008` COMPLETE; `PIL-BE-AUT-001/003/004/005/006` COMPLETE; `PIL-BE-ATE-001/003/006` COMPLETE
**Current branch:** `main` (updated after merge of PR #25 on 2026-05-01)

## Current Baseline

The separate materialization backlog was removed after completion.

Functional foundation complete:
- `apps/users/`: custom user by `matricula_funcional`, setores, papéis, centralized policies, and third-party request creation support from `PIL-BE-ACE-005`
- `apps/materials/`: `GrupoMaterial`, `SubgrupoMaterial`, `Material`, material list/search API, SCPI CSV parser, and import orchestration services
- `apps/stock/`: `EstoqueMaterial`, immutable `MovimentacaoEstoque`, initial-balance registration service, reservation movement on requisition authorization, and full-fulfillment stock exit movement
- `apps/core/`: DRF/OpenAPI infrastructure, pagination, and standard error envelope
- `apps/requisitions/`: draft creation, submit/return/discard/cancel before authorization, pending-approvals queue, authorize/refuse actions, pending-fulfillments queue, full fulfillment action, declarative transition applier, timeline events, authorization reservation side effect, and full-fulfillment stock exit side effect

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
- `RESERVA_POR_AUTORIZACAO` and `SAIDA_POR_ATENDIMENTO` are the current operational stock movements and must keep `requisicao`, `item_requisicao`, and `material` coherent through `clean()/full_clean()` plus ORM regression coverage
- Reservation write path rejects `quantidade <= 0` and revalidates `quantidade <= saldo_disponivel` under lock in the stock service itself
- Full-fulfillment stock exit rejects `quantidade <= 0`, revalidates both `saldo_fisico` and `saldo_reservado` under lock, decrements both balances, and records immutable `SAIDA_POR_ATENDIMENTO`
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
- The repository now contains API, service, stock, PostgreSQL-concurrency, and OpenAPI tests covering the delivered requisition authorization and full-fulfillment endpoints and invariants

## Recommended Next PR Sequence

1. Partial fulfillment and zero-delivery handling
   - Build on top of the full-fulfillment write path; require per-item justification and at least one delivered item greater than zero
2. Reservation release for undelivered quantities and authorized-request cancellation
   - Needed to close the loop once stock is reserved but later partially served, canceled, or otherwise reversed
3. Return / estorno / exceptional stock-exit flows
   - Must define one canonical lock acquisition order across requisition, items, and stock before adding new stock writers
4. Post-authorization/post-fulfillment notifications and ancillary side effects
   - Should remain post-commit side effects, never source of truth

## Notes For Future Agents

- Prefer backend/API-only slices while frontend remains out of active scope
- Reuse `apps/users/policies.py` from both services and views
- Keep business rules in services/use cases, not in views/serializers/admin
- Treat SCPI import as a service pipeline: parser/normalization + domain creation + stock initialization, with atomic persistence
- For anything involving stock mutation, preserve the documented transaction/locking posture and define canonical lock order before adding more stock writer flows
- In this repo phase, DB-level trigger/migration enforcement for some stock invariants may still be deferred; when that happens, document the residual risk explicitly and keep ORM-level guards/tests aligned with the decision
