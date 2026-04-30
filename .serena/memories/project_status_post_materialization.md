# Project Status — Post-Materialization

**Date:** 2026-04-29
**Status:** Django materialization COMPLETE; PIL-BE-ACE foundation COMPLETE through `PIL-BE-ACE-005`; PIL-BE-MAT-001 COMPLETE; PIL-BE-MAT-002 COMPLETE; PIL-BE-EST-001 COMPLETE; PIL-BE-MAT-003 COMPLETE; PIL-BE-IMP-001 COMPLETE; PIL-BE-IMP-002 COMPLETE; PIL-BE-REQ-001 COMPLETE
**Current branch:** `main` (latest local check on 2026-04-29)

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

## Current Validation Snapshot

- `rtk make test` passed locally on 2026-04-29 with 175 collected tests
- The import/parser baseline now includes regression coverage for BOM handling, multiline descriptions, multiline names, decimal comma quantities, and all-or-nothing persistence

## Recommended Next PR Sequence

1. `PIL-BE-REQ-001` — request and request-item models
   - Dependencies for the base slice are already in place; this becomes the next persistent workflow core
2. `PIL-BE-REQ-002` — annual public request numbering
   - Keep numbering/concurrency logic isolated and auditable right after the models land
3. `PIL-BE-REQ-003` — draft request creation
   - Reuses the delivered material search API and the request models for the first end-to-end draft flow
4. Request lifecycle/authorization slices after draft creation
   - Sequence them only after the persistent request core is merged to avoid mixing state machine work into the model PR

## Notes For Future Agents

- Prefer backend/API-only slices while frontend remains out of active scope
- Reuse `apps/users/policies.py` from both services and views
- Keep business rules in services/use cases, not in views/serializers/admin
- Treat SCPI import as a service pipeline: parser/normalization + domain creation + stock initialization, with atomic persistence
- For anything involving stock mutation, preserve the documented transaction/locking posture before outbound movement flows are introduced
