# Project Status — Post-Materialization

**Date:** 2026-04-30
**Status:** Django materialization COMPLETE; PIL-BE-ACE foundation COMPLETE through `PIL-BE-ACE-005`; PIL-BE-MAT-001 COMPLETE; PIL-BE-MAT-002 COMPLETE; PIL-BE-EST-001 COMPLETE; PIL-BE-MAT-003 COMPLETE; PIL-BE-IMP-001 COMPLETE; PIL-BE-IMP-002 COMPLETE; PIL-BE-REQ-001 COMPLETE; `PIL-BE-REQ-002/003/004/005/007/008` COMPLETE; `PIL-BE-AUT-001` COMPLETE for listing only
**Current branch:** `main` (updated after merge of PR #23 on 2026-04-30)

## Current Baseline

The separate materialization backlog was removed after completion.

Functional foundation complete:
- `apps/users/`: custom user by `matricula_funcional`, setores, papéis, centralized policies, and third-party request creation support from `PIL-BE-ACE-005`
- `apps/materials/`: `GrupoMaterial`, `SubgrupoMaterial`, `Material`, material list/search API, SCPI CSV parser, and import orchestration services
- `apps/stock/`: `EstoqueMaterial`, immutable `MovimentacaoEstoque`, and initial-balance registration service
- `apps/core/`: DRF/OpenAPI infrastructure, pagination, and standard error envelope

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
- No manual stock adjustment via admin
- Requisition public numbers start only on first submission for authorization, never on draft creation
- Requisition public numbering is annual and concurrency-safe
- A returned-to-draft requisition keeps its existing `numero_publico`
- Pending-approvals listing must contain only `aguardando_autorizacao` requests in the caller scope
- Pre-authorization discard is physical only for never-formalized drafts; pre-authorization cancel is logical
- This requisition slice does not yet reserve or decrement stock

## Current Validation Snapshot

- `rtk make test` passed locally on 2026-04-29 with 175 collected tests before the requisition workflow slice landed
- For the merged requisitions pre-authorization slice, the validated local flow was `rtk make init` then `rtk make setup` before pytest
- Requisitions services/API/model tests passed locally for the merged slice
- OpenAPI route assertions for the requisitions endpoints passed locally
- Swagger UI HTML-rendering tests remained a separate environment issue and were not used as a blocker for the requisitions domain PR

## Recommended Next PR Sequence

1. `PIL-BE-AUT-003` — authorization total/partial endpoint and persistence
   - Highest continuity from the merged pre-authorization slice; adds the first real decision path from the pending queue
2. `PIL-BE-AUT-004` — full-request refusal
   - Shares the same actor scope, queue entrypoint, and authorization state machine boundary as AUT-003
3. `PIL-BE-AUT-005` — stock reservation movement on authorization
   - Land only after AUT-003 defines the authoritative authorization write path
4. `PIL-BE-AUT-006` — balance recalculation and locking during authorization
   - Concurrency hardening should sit on top of the final reservation path, not before it

## Notes For Future Agents

- Prefer backend/API-only slices while frontend remains out of active scope
- Reuse `apps/users/policies.py` from both services and views
- Keep business rules in services/use cases, not in views/serializers/admin
- Treat SCPI import as a service pipeline: parser/normalization + domain creation + stock initialization, with atomic persistence
- For anything involving stock mutation, preserve the documented transaction/locking posture before outbound movement flows are introduced
