# ERP-SAEP-v2 overview

ERP-SAEP is an auxiliary ERP for SAEP (Servico de Agua e Esgoto de Pirassununga), initially focused on a robust backend for warehouse/material requisition workflows.

The current repository is still documentation-heavy. The active implementation direction is backend/API only: domain modeling, persistence, authentication, authorization, stock/requisition workflows, SCPI CSV import, auditability, and technical/administrative operation paths. Frontend work is explicitly out of current scope and remains future planning only.

Django materialization is tracked separately in `docs/backlog/backlog-materializacao-django.md` with `MAT-*` tasks. The materialization direction is manual minimum bootstrap, without external project generators. When materialized, Django apps should live under `apps/`, while `config/` remains responsible for project bootstrap and settings. `apps/core/` is reserved for technical API infrastructure only; `apps/users/` is created later by `PIL-BE-ACE-001`.

Primary pilot goal: validate the core flow with real users while keeping paper control in parallel: login by matricula, role permissions, initial SCPI CSV material/stock load, create requisition, submit for authorization, authorize/reject, reserve stock, fulfill in warehouse, decrement stock, release undelivered reservation, basic request timeline, and essential notifications.

Important references:
- `AGENTS.md` contains project instructions and guardrails.
- `docs/design-acesso-rapido/stack.md` records stack and architectural decisions.
- `docs/design-acesso-rapido/api-contracts.md` records DRF/API contract rules.
- `docs/design-acesso-rapido/matriz-invariantes.md` records critical domain invariants.
- `docs/design-acesso-rapido/matriz-permissoes.md` records permission/scope rules.
- `docs/backlog/backlog-materializacao-django.md` is the technical Django materialization backlog and must be completed before `PIL-*` functional work.
- `docs/backlog/backlog-tecnico-piloto.md` is the initial pilot functional backlog.
- `docs/backlog/backlog-tecnico-mvp.md` is the later MVP backlog.
- `docs/coderabbit-guidelines.md` records code review/domain invariants.

Known operational TODO:
- When the real Django project/apps are materialized, review `.github/workflows/ci.yml` so the ephemeral CI schema rebuild does not depend on a fixed app list and instead reflects the full active codebase.

Current top-level structure:
- `.github/` GitHub metadata/workflows.
- `.serena/` Serena project config and memories.
- `docs/` design docs and backlog.
- `Makefile` local development routines.
- `AGENTS.md` agent instructions.