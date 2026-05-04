# Frontend pilot architecture and bloco 0

Recorded from the 2026-05-02 architecture session.

## Macro decision
- Frontend pilot is active scope now.
- Shape is a separate SPA in `frontend/`, same repo, not React inside Django templates.
- Backend remains source of truth for domain, auth, authorization, stock, and state transitions.
- Frontend work is blocked until the backend enablement block (`bloco 0`) lands.

## Approved stack
- `pnpm`
- React + TypeScript + Vite
- TanStack Query
- TanStack Router with file-based routing
- TanStack Table
- React Hook Form + Zod
- `openapi-typescript` + `openapi-fetch`
- Tailwind CSS + shadcn/ui + Radix UI
- Playwright

## UX/product rules
- desktop-first, PT-BR, single light theme
- worklist-first UX
- canonical detail route is `/requisicoes/:id`
- operational context comes from `?contexto=autorizacao|atendimento`
- one operational `papel` principal per user in the pilot; frontend derives capabilities from that single `papel`
- solicitante UX is more guided; authorization/fulfillment UX can be denser
- notifications are contextual support only and second wave, not first-cut center of navigation

## Auth/API boundary
- Django session auth + CSRF, no JWT in pilot
- frontend uses exported OpenAPI file `frontend/openapi/schema.json`
- `Makefile` is the repo entrypoint even though frontend uses `pnpm` internally

## Bloco 0 backend APIs required before SPA work
1. `GET /api/v1/auth/csrf/`
2. `POST /api/v1/auth/login/`
3. `POST /api/v1/auth/logout/`
4. `GET /api/v1/auth/me/`
5. `GET /api/v1/users/beneficiary-lookup/?q=...`
6. `GET /api/v1/requisitions/`
7. `GET /api/v1/requisitions/{id}/`
8. explicit draft-update action using full replacement semantics

## Bloco 0 order approved in session
1. auth/session
2. beneficiary lookup
3. canonical requisition reads
4. explicit draft update

## Issue breakdown created in session
- `#31` auth/session for SPA
- `#32` beneficiary lookup
- `#33` canonical requisition reads
- `#34` explicit draft update
- `#35` minimum seed + Makefile
- `#36` frontend scaffold + Makefile
- `#37` login/bootstrap SPA
- `#38` minhas requisicoes + canonical detail
- `#39` create/edit draft + submit
- `#40` approvals queue + decisions
- `#41` fulfillment queue + fulfill flows
- `#42` initial frontend CI
- `#43` Playwright local + CI phase 2
- `#44` notifications second wave

## Status at end of session
- `#31` is already `ready-for-agent`
- frontend architecture is documented in `docs/design-acesso-rapido/frontend-arquitetura-piloto.md`
- macro decision is documented in `docs/adr/0001-frontend-piloto-spa-separada.md`
- backlog and AGENTS docs were updated to enforce the bloco 0 gate

## Update after issue #36
- `frontend/` now exists with the SPA foundation materialized.
- Delivered base includes Vite, React, TypeScript, TanStack Router file-based routing, TanStack Query provider, Tailwind CSS baseline, `openapi-fetch` client, Vitest smoke tests, and Playwright smoke E2E.
- Official repo entrypoints are `rtk make frontend-init`, `frontend-gen-api`, `frontend-dev`, `frontend-build`, `frontend-lint`, `frontend-test`, and `frontend-e2e`.
- `frontend/openapi/schema.json`, `frontend/src/shared/api/schema.d.ts`, and `frontend/src/routeTree.gen.ts` are generated artifacts and should not be edited manually.
- Next frontend slices move to `#37` login/bootstrap, `#42` initial frontend CI, then operational worklists and draft/detail flows.
