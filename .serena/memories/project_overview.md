# ERP-SAEP-v2 overview

ERP-SAEP is an auxiliary ERP for SAEP (Servico de Agua e Esgoto de Pirassununga), initially focused on a robust backend for warehouse/material requisition workflows.

The current repository is still documentation-heavy. The active implementation direction is backend/API only: domain modeling, persistence, authentication, authorization, stock/requisition workflows, SCPI CSV import, auditability, and technical/administrative operation paths. Frontend work is explicitly out of current scope and remains future planning only.

When the Django project is materialized, Django apps should live under the `apps/` directory, while `config/` remains responsible for project bootstrap and settings.

Primary pilot goal: validate the core flow with real users while keeping paper control in parallel: login by matricula, role permissions, initial SCPI CSV material/stock load, create requisition, submit for authorization, authorize/reject, reserve stock, fulfill in warehouse, decrement stock, release undelivered reservation, basic request timeline, and essential notifications.

Important references:
- `AGENTS.md` contains project instructions and guardrails.
- `docs/design/stack.md` records stack and architectural decisions.
- `docs/design/modelo-dominio-regras.md` records domain model and business rules.
- `docs/design/processos-almoxarifado.md` records warehouse/requisition process flows.
- `docs/design/criterios-aceite.md` records acceptance criteria.
- `docs/design/importacao-scpi-csv.md` records SCPI CSV import rules.
- `docs/backlog/backlog-tecnico-piloto.md` is the initial pilot backlog.
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