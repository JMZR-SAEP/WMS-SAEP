# uv Dependency Management

**Status:** Adopted in PR #11 (2026-04-27)  
**Replaces:** `pip` + `requirements.txt` → `uv` + `pyproject.toml` + `uv.lock`

## Overview

Project now uses `uv` for Python environment and dependency management. This provides:
- 3-5x faster environment setup
- Deterministic lockfile (`uv.lock`) for reproducible CI/CD
- Automatic venv creation and management
- Simplified local development workflow

## Installation & Setup

### Prerequisites
- Python 3.14 (via `.python-version`)
- `uv` binary installed on system (see https://docs.astral.sh/uv/getting-started/)

### Local Development Workflow

```bash
# Initial setup
rtk make prepare    # Materializes .env from .env.example
rtk make init       # Runs: uv sync (creates .venv, installs deps)

# After editing dependencies in pyproject.toml
rtk uv sync         # Updates .venv to match pyproject.toml + uv.lock

# Running commands
rtk uv run python manage.py <cmd>    # Run Django commands
rtk uv run pytest                     # Run tests
rtk make test                         # Convenience wrapper
rtk make run                          # Start dev server
```

## Dependency Management

### Files

- **`pyproject.toml`**: Dependency declarations with version ranges (e.g., `Django>=6.0,<7`)
- **`uv.lock`**: Deterministic lock file with exact versions, hashes, and URLs. Do not edit manually.
- **`.python-version`**: Python 3.14 specification for pyenv/asdf/setup-python

### Adding/Updating Dependencies

```bash
# Add new dependency
rtk uv add package-name                    # Adds to pyproject.toml + regenerates uv.lock
rtk uv add --group dev pytest-cov         # Add to dev group

# Update all dependencies (breaking)
rtk uv lock --upgrade                      # Regenerates uv.lock with newest compatible versions

# Update specific package
rtk uv lock --upgrade-package package-name # Updates single package in lock

# Sync local environment after lock changes
rtk uv sync
```

### Version Pinning Strategy

- **Major version pinning** in `pyproject.toml`: `Django>=6.0,<7` (allows minor/patch updates)
- **Exact version pinning** in `uv.lock`: All packages pinned to exact version for reproducibility
- Trade-off: Flexibility in `pyproject.toml`, determinism in `uv.lock` and CI

## CI/CD Integration

**GitHub Actions:** `.github/workflows/ci.yml`
- Uses `astral-sh/setup-uv@v8.1.0` with caching enabled
- Lint job: `uv run ruff check/format`
- Test job: `uv sync --locked && uv run pytest`
  - `--locked` prevents uv.lock modifications in CI (safety)
  - PostgreSQL service configured for database tests

## Cleanup and Ephemeral Environment

### Reset Local Environment
```bash
rtk make clean      # Removes caches/artifacts, keeps .venv
rtk make veryclean  # Removes .venv + caches + local migrations
```

After `veryclean`, run `rtk make init` to recreate .venv.

### Ephemeral Database with Migrations
```bash
rtk make setup      # Resets PostgreSQL public schema, recreates migrations, applies
rtk make resetdb    # Reapplies migrations without deleting migration files
```

## Troubleshooting

### `uv: command not found`
- `uv` binary not in PATH
- Install from https://docs.astral.sh/uv/getting-started/
- Or use system package manager: `brew install uv` (macOS), `apt install pipx && pipx install uv` (Linux)

### `.venv` removed but `uv` commands fail
- Run `rtk uv sync` to recreate .venv

### Dependency conflict in `uv.lock`
- Check `pyproject.toml` for conflicting version ranges
- Run `rtk uv lock --upgrade` to resolve
- If unresolvable, adjust ranges in `pyproject.toml`

### CI fails with setup-uv
- Ensure `setup-uv@v8.1.0` supports Python 3.14 (tracked in PR #11)
- Update action version if needed: `astral-sh/setup-uv@v<latest>`

## References

- **Official Docs**: https://docs.astral.sh/uv/
- **Project Integration**: `pyproject.toml`, `.github/workflows/ci.yml`, `Makefile`, `AGENTS.md`
- **Dependency Baseline**: See `docs/design-acesso-rapido/stack.md` for current stack versions
- **CI Setup**: `.github/workflows/ci.yml` for GitHub Actions integration
