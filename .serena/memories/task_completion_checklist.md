# Task completion checklist

Before considering implementation work complete:
- Re-read the relevant design/backlog docs for the touched domain area.
- Ensure rules of business/domain are in services/use cases, not views/serializers/models/signals/templates/admin actions.
- Ensure contextual authorization is centralized and applied consistently in views and services.
- For API work, confirm compliance with `docs/design/api-contracts.md`: session auth default or justified override, permissions, policies, serializers, status codes, standard error envelope, filters/pagination/ordering where applicable, OpenAPI schema, and contract tests.
- For stock/ledger/requisition state changes, confirm `transaction.atomic()`, deterministic locking with `select_for_update()` where needed, and tests for critical invariants.
- For bug fixes, add a regression test that would fail before the fix.
- For schema/model changes in the ephemeral dev phase, recreate local migrations and rebuild the local database before validation; do not treat generated app migrations as deliverables or commit them unless project policy changes.
- For non-structural changes, prefer focused validation over full environment rebuilds.
- Run the appropriate validation command with `rtk`. Broad default when code exists: `rtk make test`.
- Inspect `rtk git status --short` and summarize only files changed for the task.

High-risk residuals to call out in final responses: tests not run, missing PostgreSQL/concurrency coverage, OpenAPI not regenerated, or any deviation from documented domain invariants.