# Frontend analytics technical debt

Context: PR #5 / issue #69 implemented internal frontend analytics and support-error details without PII.

Debt recorded on 2026-05-12:

- `FrontendAnalyticsEvent.papel` is protected at the application/ORM layer by `FrontendAnalyticsEvent.save()` plus `FrontendAnalyticsEventQuerySet.update()` refusing `papel` updates.
- CodeRabbit requested a DB-level PostgreSQL trigger/migration to make `papel` immutable even for direct SQL updates.
- This was intentionally not implemented in PR #5 because the repo is still in an ephemeral migration phase: `apps/**/migrations/*.py` are ignored, `rtk make setup` regenerates local migrations, and the documented rule says migrations are not normal versioned deliverables yet.
- Future hardening task: when the project moves out of ephemeral migrations or defines a supported path for versioned DB triggers, add a DB-level invariant for `apps.analytics.models.FrontendAnalyticsEvent.papel` immutability, preferably a PostgreSQL `BEFORE UPDATE` trigger that raises when `NEW.papel <> OLD.papel`, plus a migration and direct-SQL/DB-level regression test.
- Until then, do not present DB-level immutability for analytics `papel` as implemented; current guarantee is ORM/service-level only.