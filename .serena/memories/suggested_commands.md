# Suggested commands

Always prefix shell commands with `rtk` per `/Users/jmzr/.codex/RTK.md`. If a command shape is not supported by `rtk`, use `rtk proxy <cmd>`.

Project routines from `Makefile`:
- `rtk make help` - list available routines.
- `rtk make prepare` - create venv and materialize `.env` from `.env.example`.
- `rtk make init` - recreate Python environment and install dependencies.
- `rtk make setup` - reset local DB state, recreate local migrations, migrate, and collect static.
- `rtk make clean` - remove local caches/artifacts without touching the database.
- `rtk make cleanall` - clean local artifacts and reset PostgreSQL.
- `rtk make veryclean` - remove venv and generated local migrations/caches.
- `rtk make resetpostgres` - drop/recreate PostgreSQL public schema using `DATABASE_URL`.
- `rtk make test` - run tests with `config.settings.test`.
- `rtk make run` - run Django development server with `config.settings.dev`.
- `rtk make resetdb` - migrate the current database to zero and back without deleting local migration files.

Materialization workflow guidance:
- Complete `docs/backlog/backlog-materializacao-django.md` (`MAT-*`) before starting `PIL-*` pilot tasks.
- Use `config.settings.dev` for development and `config.settings.test` for tests; there is no separate `config.settings.test_postgres` module in the current plan.
- Materialization must not create `apps/users/` or any ERP-SAEP domain app; `apps/core/` is technical API infrastructure only.

Ephemeral workflow guidance:
- For non-structural tasks, prefer incremental local work plus focused tests.
- For schema/model changes, reset the database and rebuild local migrations before final validation.
- Generated local migrations are temporary materialization artifacts, not normal deliverables.

Useful Darwin/macOS development commands:
- `rtk pwd`
- `rtk ls -la`
- `rtk rg --files`
- `rtk rg "pattern" path`
- `rtk sed -n '1,200p' path`
- `rtk git status --short`
- `rtk git diff -- path`
- `rtk proxy find . -maxdepth 3 -type f`

Serena was initialized for `/Users/jmzr/Dev/ERP-SAEP-v2` with project name `ERP-SAEP-v2`.
