# Code style and conventions

General style:
- Follow existing repository patterns and documented design decisions before introducing new abstractions.
- Keep changes narrow and aligned with domain boundaries.
- Prefer services/use cases for business logic and policies for contextual authorization.
- Keep views, serializers, templates, admin actions, signals, and management commands thin.
- Use explicit contracts for APIs and update OpenAPI/tests when contracts change.
- Follow `docs/design-acesso-rapido/api-contracts.md` as the canonical API contract standard.
- Add regression tests for every bug fix.

Django/DRF conventions:
- The materialization may enable Django auth provisionally for bootstrap/Admin/DRF, but `apps/users/` and the custom user model are created in `PIL-BE-ACE-001`; functional registration/matricula is the login identifier before any real pilot/domain use.
- When using a custom auth backend for matricula login, preserve compatibility with Django's standard auth entrypoints (`authenticate(username=..., password=...)`, admin login, session flows) instead of requiring callers to pass only custom kwarg names.
- For auth hardening fixes, add regression coverage for the real Django auth path, not only backend-specific helper calls.
- Use DRF serializers for input validation, local payload coherence, typing, and output representation.
- Use thin ViewSets/APIViews and explicit permissions/querysets to prevent IDOR and cross-department access.
- Version formal API endpoints under `/api/v1/`.
- Use session authentication with CSRF by default for `/api/v1/`; token/JWT is deferred until there is a non-session consumer such as mobile, external integration, CLI, or machine-to-machine access.
- Do not wrap successful detail/action responses in a global success envelope; lists use the standard pagination envelope.
- Use the standard API error envelope with English `code`, PT-BR `message`, structured `details`, and `trace_id`.
- Use `django-filter` for typed list filters, plus DRF search/ordering with explicit allowlists.
- Put critical business rules in `services.py` or a clear service module.
- Put contextual access rules in `policies.py` or equivalent.
- For writes, services must validate profile, department/scope, and domain object state.
- For SCPI-backed catalogs, do not rely only on `RegexValidator` or `full_clean()` when the code format is structural; pair model validation with DB-level constraints when bypass via ORM create/bulk paths would be a real risk.
- Avoid exposing admin add/change/delete for SCPI-official catalog fields unless the task explicitly introduces a controlled technical import/maintenance flow.

Testing conventions:
- Business-critical flows need tests for happy path, permission denied, domain violation, contract/error behavior, and concurrency when stock/ledger is affected.
- PostgreSQL behavior matters; SQLite tests do not prove row locking, partial indexes, constraints, or concurrency.
- API changes need contract tests.
- API contract tests should cover auth, permission denied, invalid input/error envelope, domain conflict when applicable, pagination/filtering/ordering for lists, and OpenAPI request/response coverage.

Migrations convention:
- Local app migrations are ephemeral and ignored during this phase. Do not treat generated migrations as source of truth; delete/recreate them before validation.

Agent/shell convention:
- Repository instruction imports `/Users/jmzr/.codex/RTK.md`; shell commands should be prefixed with `rtk`.
- If `rtk` cannot express a needed command form, use `rtk proxy <cmd>`.
