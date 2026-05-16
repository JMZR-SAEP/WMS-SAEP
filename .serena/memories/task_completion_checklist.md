# Task completion checklist

Before considering implementation work complete:
- If working on Django materialization, treat it as completed (no materialization backlog).
- Re-read relevant design/backlog docs for touched domain area.
- Ensure business rules are in `services.py`, not views/serializers/models/signals/templates/admin.
- Ensure contextual authorization is centralized in `policies.py` and applied consistently in views + services.
- For API work, confirm `docs/design-acesso-rapido/api-contracts.md` compliance: session auth default or override, permissions, policies, serializers, status codes, error envelope, filters/pagination/ordering, OpenAPI schema, contract tests.
- For requisitions/stock mutations: confirm `transaction.atomic()`, `select_for_update()` inside tx, Port/Adapter pattern (via `StockPort`) if stock is involved, and critical invariant tests.
- For parser/import: validate real file shape (BOM, delimiter, multiline, mandatory fields, numeric normalization).
- For import orchestration: keep parser, domain creation, stock init inside atomic all-or-nothing boundary.
- For bug fixes: add regression test that fails before the fix.
- For schema/model changes in ephemeral phase: recreate local migrations, rebuild local DB.
- For non-structural changes: prefer focused validation over full rebuilds.
- Run appropriate validation: `rtk make test` broad default.
- Inspect `rtk git status --short`, summarize only task-related file changes.

High-risk residuals to call out in final responses: tests not run, missing PostgreSQL/concurrency coverage, OpenAPI not regenerated, or any deviation from documented domain invariants.
