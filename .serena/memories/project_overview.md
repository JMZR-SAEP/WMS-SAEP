# WMS-SAEP overview

WMS-SAEP is an auxiliary WMS for SAEP (Servico de Agua e Esgoto de Pirassununga), initially focused on a robust backend for warehouse/material requisition workflows.

The implementation direction remains backend/API-first: domain modeling, persistence, authentication, authorization, stock/requisition workflows, SCPI CSV import, auditability, and technical/administrative operation paths. Frontend work was reopened in this session as active pilot scope, but only as a separate SPA in `frontend/` and only after the backend enablement block (`bloco 0`) is completed.

The initial Django materialization has already been completed and the separate materialization backlog was removed. The current active scope is backend/API pilot and MVP work. Django apps live under `apps/`, while `config/` remains responsible for project bootstrap and settings. `apps/core/` is reserved for technical API infrastructure only.

Primary pilot goal: validate the core flow with real users while keeping paper control in parallel: login by matrícula, role permissions, initial SCPI CSV material/stock load, create requisition, submit for authorization, authorize/reject, reserve stock, fulfill in warehouse, decrement stock, release undelivered reservation, basic request timeline, and essential notifications.

Current delivered backend baseline:
- Access/auth foundation through `PIL-BE-ACE-005`
- Materials catalogs through `PIL-BE-MAT-002`
- Stock base through `PIL-BE-EST-001`
- Material search/list API through `PIL-BE-MAT-003`
- SCPI CSV parser + import/bootstrap stock flow through `PIL-BE-IMP-001` and `PIL-BE-IMP-002`
- Requisition draft/formalization/pre-authorization flow through `PIL-BE-REQ-002/003/004/005/007/008`
- Authorization queue, authorize/refuse endpoints, stock reservation movement, and locking hardening through `PIL-BE-AUT-001/003/004/005/006`
- Warehouse fulfillment queue, full fulfillment endpoint, stock exit movement, and withdrawal metadata through `PIL-BE-ATE-001/003/006`

Important references:
- `AGENTS.md` contains project instructions and guardrails.
- `docs/design-acesso-rapido/stack.md` records stack and architectural decisions.
- `docs/design-acesso-rapido/api-contracts.md` records DRF/API contract rules.
- `docs/design-acesso-rapido/matriz-invariantes.md` records critical domain invariants.
- `docs/design-acesso-rapido/matriz-permissoes.md` records permission/scope rules.
- `docs/backlog/backlog-tecnico-piloto.md` is the active pilot backlog and now includes bloco 0 plus blocked frontend slices.
- `docs/backlog/backlog-tecnico-mvp.md` is the later MVP backlog.
- `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` records the operational SPA architecture.
- `docs/adr/0001-frontend-piloto-spa-separada.md` records the macro frontend decision.
- `docs/agents/` records GitHub issue tracker, triage labels, and domain-doc routing for issue-oriented skills.
- `docs/coderabbit-guidelines.md` records code review/domain invariants.

Current top-level structure:
- `.github/` GitHub metadata/workflows.
- `.serena/` Serena project config and memories.
- `docs/` design docs and backlog.
- `apps/` Django apps.
- `config/` Django bootstrap/settings.
- `Makefile` local development routines, including official `frontend-*` entrypoints for the SPA.
- `AGENTS.md` agent instructions.
- `frontend/` SPA foundation for the pilot.

Current near-term implementation frontier:
- login/bootstrap of the SPA on top of the delivered scaffold
- initial frontend CI over generated API types, lint, and build
- first-cut operational flows after the scaffold: `Minhas requisições`, draft editing/submission, authorization queue, and fulfillment queue
- notifications in the SPA only as second wave, while backend notifications remain post-commit side effects and never domain truth
- physical stock reversal / return / estorno flows after the frontend enablement path is stabilized
