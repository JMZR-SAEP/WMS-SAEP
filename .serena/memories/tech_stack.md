# Tech stack

Current active stack for WMS-SAEP:
- Python compatible with Django 6.
- Django 6 monolith.
- Django REST Framework for APIs.
- PostgreSQL as the required database for pilot/production behavior.
- Django ORM.
- drf-spectacular for OpenAPI schema.
- django-filter for typed list endpoint filters.
- django-allauth for auth support, with configuration deferred until access/authentication tasks.
- python-dotenv for local `.env` loading during materialization.
- django-cors-headers for conservative CORS configuration.
- pytest, pytest-django, ruff, coverage, and pre-commit as the initial quality/tooling base.
- factory_boy as the chosen standard for test data generation.

Approved pilot frontend stack:
- separate SPA in `frontend/`
- `pnpm` as Node package manager, integrated through repo `Makefile`
- React + TypeScript + Vite
- TanStack Query, TanStack Router, TanStack Table
- React Hook Form + Zod
- `openapi-typescript` + `openapi-fetch`
- Tailwind CSS + shadcn/ui + Radix UI
- Playwright for E2E
- exported OpenAPI input file at `frontend/openapi/schema.json`
- generated OpenAPI types at `frontend/src/shared/api/schema.d.ts`
- generated TanStack Router tree at `frontend/src/routeTree.gen.ts`

Current dependency baseline after the 2026-04-27 audit/upgrade (`d7702de chore: upgrade python dependencies`):
- Django 6.0.4, djangorestframework 3.17.1, drf-spectacular 0.29.0.
- django-filter 25.2, django-allauth 65.16.1, django-cors-headers 4.9.0.
- psycopg/psycopg-binary 3.3.3, python-dotenv 1.2.2.
- pytest 9.0.3, pytest-django 4.12.0, coverage 7.13.5, ruff 0.15.12, pre-commit 4.6.0, factory_boy 3.3.3.

Materialization baseline:
- Django materialization is complete and no longer tracked in a separate backlog file.
- Functional pilot slices now landed through `PIL-BE-ACE-005`, `PIL-BE-MAT-002`, `PIL-BE-EST-001`, `PIL-BE-MAT-003`, `PIL-BE-IMP-001`, `PIL-BE-IMP-002`, and `PIL-BE-REQ-001`.

Current state: Django project initialized with technical infrastructure plus active domain apps `users`, `materials`, `stock`, and `requisitions`.

**Backend module structure** (after requisitions refactoring PR #22):
- `config/` → settings, URLs, ASGI/WSGI, bootstrap.
- `apps/core/` → API infrastructure, pagination, error envelope, schema helpers.
- `apps/users/` → custom user, sectors, role/policy foundation.
- `apps/materials/` → `GrupoMaterial`, `SubgrupoMaterial`, `Material`, list/search API, SCPI CSV parsing.
- `apps/stock/` → `EstoqueMaterial`, immutable `MovimentacaoEstoque`, stock admin, initial-balance bootstrap, `StockAdapter` (implements `StockPort` from requisitions).
- `apps/requisitions/` (refactored):
  - `models.py` → `Requisicao`, `ItemRequisicao`, `HistoricalRecord` (via django-simple-history).
  - `domain/state_machine.py` → declarative state machine with transition table.
  - `policies.py` → centralized authorization checks (contextual: object-aware, scope-aware).
  - `services.py` → business orchestration and domain rules (reduced scope after module extraction).
  - `queries.py` → query helpers (load, lock, validate patterns).
  - `sequences.py` → public number and ID generation.
  - `idempotency.py` → payload idempotency with cached result.
  - `ports.py` → `StockPort` interface (Protocol) for decoupled stock operations.
  - `serializers.py` → DRF serializers for API input/output.
  - `views.py` → thin APIViews/ViewSets.
- `apps/notifications/` → in-process pub/sub event bus (`core/events.py`), notification models, domain event subscribers.

**Port/Adapter pattern** (ADR 0002 — Accepted):
- `StockPort` (Protocol): `apps/requisitions/ports.py`.
- `StockAdapter` (implementation): `apps/stock/adapters.py`.
- Prevents circular coupling; requires no direct import of requisitions in stock.
- Port methods: `aplicar_reservas_autorizacao`, `liberar_reservas_cancelamento`, `aplicar_saidas_e_liberacoes_retirada`.

Initial settings are `config.settings.base`, `config.settings.dev`, and `config.settings.test`; do not create a separate `test_postgres` settings module.
- PostgreSQL is configured through `DATABASE_URL`; no Docker Compose or production settings are part of the active baseline.
- `frontend/` is now materialized with Vite, Tailwind CSS, TanStack Router file-based routing, TanStack Query provider wiring, `openapi-fetch` client bootstrap, Vitest smoke tests, and Playwright smoke E2E.

Current validation snapshot:
- `rtk make test` passed locally on 2026-04-29 with 175 collected tests.
- The current suite covers API pagination/search contracts, SCPI parser edge cases, import all-or-nothing behavior, and initial stock-movement consistency.

Current scope rule: frontend pilot work is now part of the active implementation scope, but only through the approved separate SPA architecture and only after the backend enablement block (`bloco 0`) is completed. Backend/API work, domain rules, persistence, authentication, authorization, imports, internal/admin flows, and tests remain the source-of-truth frontier; do not introduce server-rendered UI work or a parallel frontend shape outside the approved SPA path.

Typing/tooling rule: mypy, django-stubs, and djangorestframework-stubs are intentionally out of the current stack and may be reconsidered later if static typing becomes an explicit project discipline.

Async rule: Celery is not in the pilot critical path, and no Redis dependency is part of the current stack definition. The SCPI import path already lives in reusable services and can later be wrapped by async orchestration without duplicating domain rules.

Production shape under consideration:
- Nginx -> Gunicorn -> Django -> PostgreSQL.
- Docker Compose or Python/systemd deployment may be chosen later and should be recorded before production deployment.

Serena project config is set to language support: python, markdown, yaml.
