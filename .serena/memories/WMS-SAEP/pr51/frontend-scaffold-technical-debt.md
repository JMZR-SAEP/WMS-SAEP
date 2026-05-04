# PR 51 frontend scaffold technical debt

Context: PR #51 delivered the pilot SPA foundation in `frontend/`, integrated the Makefile entrypoints, exported the OpenAPI contract for the frontend client, and left the repository ready for the first operational frontend slices.

Residual debt / follow-up:
- Frontend authentication is still scaffold-only. `/login` remains a placeholder, there is no session bootstrap from `GET /api/v1/auth/me/`, and route guards/home-by-role resolution are not implemented yet. This is the next mandatory slice before any protected operational flow is treated as real UI.
- The repository still lacks the initial frontend CI workflow. The next CI slice should run at least the generated-artifact and frontend quality gates: `pnpm tsr generate` with drift detection for `frontend/src/routeTree.gen.ts`, `frontend-gen-api`/OpenAPI drift protection, lint, typecheck, unit smoke tests, and the Playwright smoke test.
- The `features/` tree now exists only as scaffold directories. Keep domain logic out of `shared/` and avoid expanding placeholder route files with real business behavior; move each real slice into `src/features/{auth,materials,requisitions,approvals,fulfillment}/` as soon as implementation starts.

Validation snapshot after review hardening:
- `pytest tests/test_api_schema.py tests/users/test_auth_api.py -q` passed with 35 tests.
- `frontend` eslint passed.
- `frontend` `tsc -b` passed.
- `frontend` vitest passed.
- `frontend` Playwright smoke passed after enabling the Vite dev proxy for `/api`.
