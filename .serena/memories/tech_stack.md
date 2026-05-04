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

Current state: Django project initialized with technical infrastructure plus active domain apps `users`, `materials`, and `stock`.
- `config/` owns settings, URLs, ASGI/WSGI, and project bootstrap.
- `apps/core/` is technical API infrastructure only; it hosts pagination, error envelope, schema helpers, and non-domain API utilities.
- `apps/users/` provides the custom user, sectors, role/policy foundation, and third-party request creation permission baseline.
- `apps/materials/` now contains `GrupoMaterial`, `SubgrupoMaterial`, `Material`, material list/search API, SCPI CSV parsing/normalization, and import orchestration services.
- `apps/stock/` now contains `EstoqueMaterial`, immutable `MovimentacaoEstoque`, stock admin protections, and `registrar_saldo_inicial()` for import bootstrap.
- Initial settings are `config.settings.base`, `config.settings.dev`, and `config.settings.test`; do not create a separate `test_postgres` settings module.
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
