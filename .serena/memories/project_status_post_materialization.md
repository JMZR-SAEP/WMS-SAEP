# Project Status — Post-Materialization

**Date:** 2026-04-28  
**Status:** Django materialization COMPLETE; PIL-BE-ACE foundation COMPLETE; PIL-BE-MAT-001 COMPLETE; PIL-BE-MAT-002 COMPLETE; PIL-BE-EST-001 COMPLETE  
**Current branch:** main (latest local check on 2026-04-28)

## Current Baseline

Materialization (`MAT-000`..`MAT-006`) is complete.

Functional foundation complete:
- `apps/users/`: custom user by `matricula_funcional`, setores, papéis, centralized policies
- `apps/materials/`: `GrupoMaterial`, `SubgrupoMaterial`, `Material`
- `apps/stock/`: `EstoqueMaterial` with `saldo_fisico`, `saldo_reservado`, calculated `saldo_disponivel`
- `apps/core/`: DRF/OpenAPI infrastructure, pagination, error envelope

Technical baseline:
- Django 6.0 + DRF + drf-spectacular + django-filter
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
- SCPI-backed material fields are read-only in normal admin/operational flows
- `saldo_disponivel = saldo_fisico - saldo_reservado`
- No manual stock adjustment via admin

## Current Validation Snapshot

- 120 tests passing at the last recorded local validation for this baseline
- Lint/test CI baseline was green when this state was recorded

## Recommended Next PR Sequence

1. `PIL-BE-MAT-003` — material search API/service
   - Best next slice: low coupling, backend/API-only, unlocks request creation
2. `PIL-BE-REQ-001` — request and request-item models
   - Establishes the persistent request-flow core
3. `PIL-BE-REQ-002` — annual public request numbering
   - Keep concurrency/numbering logic narrowly auditable
4. `PIL-BE-REQ-003` — draft request creation
   - Uses search + request models and enforces initial stock/material validity

## Secondary Path

If loading real data becomes more urgent than request flow:
- `PIL-BE-IMP-001` can run earlier as an isolated SCPI CSV parser/normalizer PR
- `PIL-BE-IMP-002` needs extra care because it pulls in initial stock-entry movement semantics close to the future stock-movement/audit surface

## Notes For Future Agents

- Prefer backend/API-only slices while frontend remains out of active scope
- Reuse `apps/users/policies.py` from both services and views
- Keep business rules in services/use cases, not in views/serializers/admin
- For anything involving stock mutation, preserve the documented transaction/locking posture before implementation gets deeper