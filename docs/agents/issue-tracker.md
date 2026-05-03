# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use `gh` CLI for all operations.

Infer repo from `git remote -v`. In this clone, remote points to `joaorighetto/WMS-SAEP`.

## Conventions

- **Create issue**: `gh issue create --title "..." --body "..."`
- **Read issue**: `gh issue view <number> --comments`
- **List issues**: `gh issue list` with `--state`, `--label`, `--json`, `--jq` as needed
- **Comment on issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close issue**: `gh issue close <number> --comment "..."`

## When skill says "publish to issue tracker"

Create GitHub issue.

## When skill says "fetch relevant ticket"

Run `gh issue view <number> --comments`.
