# PR 51 frontend scaffold technical debt

Context: PR #51 delivered the pilot SPA foundation in `frontend/`, integrated the Makefile entrypoints, exported the OpenAPI contract for the frontend client, and left the repository ready for the first operational frontend slices.

Residual debt / follow-up:
- Frontend authentication debt is resolved by issue #37: `/login` authenticates with matricula/password through session Django + CSRF, `/auth/me` bootstraps protected routes, `/` resolves home by `papel`, and logout clears session cache.
- The repository still lacks the initial frontend CI workflow. The next CI slice should run at least the generated-artifact and frontend quality gates: `pnpm tsr generate` with drift detection for `frontend/src/routeTree.gen.ts`, `frontend-gen-api`/OpenAPI drift protection, lint, typecheck, unit smoke tests, and the Playwright smoke test.
- New debt from #37: official `rtk make frontend-test` can still try `frontend-init` via `npx pnpm@10.15.1`; in no-network environments use local `frontend/node_modules/.bin/*` for verification or run the official init first.
- The `features/` tree now has real `features/auth` behavior. Keep future domain behavior in `src/features/{materials,requisitions,approvals,fulfillment}/` and avoid growing placeholders in `routes/`/`shared/`.

Validation snapshot after review hardening:
- `pytest tests/test_api_schema.py tests/users/test_auth_api.py -q` passed with 35 tests.
- `frontend` eslint passed.
- `frontend` `tsc -b` passed.
- `frontend` vitest passed.
- `frontend` Playwright smoke passed after enabling the Vite dev proxy for `/api`.
