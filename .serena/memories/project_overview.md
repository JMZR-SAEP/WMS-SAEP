# ERP-SAEP-v2 overview

ERP-SAEP is an auxiliary ERP for SAEP (Servico de Agua e Esgoto de Pirassununga), initially focused on a robust backend for warehouse/material requisition workflows.

The active implementation direction is backend/API only: domain modeling, persistence, authentication, authorization, stock/requisition workflows, SCPI CSV import, auditability, and technical/administrative operation paths. Frontend work is explicitly out of current scope and remains future planning only.

Django materialization is tracked separately in `docs/backlog/backlog-materializacao-django.md` with `MAT-*` tasks. The materialization direction is manual minimum bootstrap, without external project generators. Django apps live under `apps/`, while `config/` remains responsible for project bootstrap and settings. `apps/core/` is reserved for technical API infrastructure only.

Primary pilot goal: validate the core flow with real users while keeping paper control in parallel: login by matrícula, role permissions, initial SCPI CSV material/stock load, create requisition, submit for authorization, authorize/reject, reserve stock, fulfill in warehouse, decrement stock, release undelivered reservation, basic request timeline, and essential notifications.

Current delivered backend baseline:
- Access/auth foundation through `PIL-BE-ACE-005`
- Materials catalogs through `PIL-BE-MAT-002`
- Stock base through `PIL-BE-EST-001`
- Material search/list API through `PIL-BE-MAT-003`
- SCPI CSV parser + import/bootstrap stock flow through `PIL-BE-IMP-001` and `PIL-BE-IMP-002`

Important references:
- `AGENTS.md` contains project instructions and guardrails.
- `docs/design-acesso-rapido/stack.md` records stack and architectural decisions.
- `docs/design-acesso-rapido/api-contracts.md` records DRF/API contract rules.
- `docs/design-acesso-rapido/matriz-invariantes.md` records critical domain invariants.
- `docs/design-acesso-rapido/matriz-permissoes.md` records permission/scope rules.
- `docs/backlog/backlog-materializacao-django.md` is the technical Django materialization backlog.
- `docs/backlog/backlog-tecnico-piloto.md` is the initial pilot functional backlog.
- `docs/backlog/backlog-tecnico-mvp.md` is the later MVP backlog.
- `docs/coderabbit-guidelines.md` records code review/domain invariants.

Known operational TODO:
- When the request/requisition workflow lands, review CI and OpenAPI checks so schema diffs and domain contracts stay explicit as the API surface grows.

Current top-level structure:
- `.github/` GitHub metadata/workflows.
- `.serena/` Serena project config and memories.
- `docs/` design docs and backlog.
- `apps/` Django apps.
- `config/` Django bootstrap/settings.
- `Makefile` local development routines.
- `AGENTS.md` agent instructions.
