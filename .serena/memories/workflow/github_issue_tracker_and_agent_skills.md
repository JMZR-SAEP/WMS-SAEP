# GitHub issue tracker and agent-skill routing

Recorded from the 2026-05-02 setup session.

## Repo issue tracker
- Official issue tracker is GitHub Issues.
- Use `gh` for issue-oriented work.
- Default triage labels are:
  - `needs-triage`
  - `needs-info`
  - `ready-for-agent`
  - `ready-for-human`
  - `wontfix`

## Repo docs for skill routing
- `CLAUDE.md` stays as pointer only: `@AGENTS.md`
- `AGENTS.md` contains the `## Agent skills` block
- `docs/agents/issue-tracker.md` documents GitHub issue usage
- `docs/agents/triage-labels.md` documents label semantics
- `docs/agents/domain.md` documents domain-doc routing

## Domain-doc routing for issue-oriented skills
- repo is single-context
- read root `CONTEXT.md`
- read root `docs/adr/`
- read `docs/design-acesso-rapido/` first
- read `docs/design-acesso-ocasional/` only when quick docs are insufficient or ambiguous

## Frontend planning issue batch from this session
- frontend pilot ADR was broken into GitHub issues `#31` through `#44`
- the first issue moved to `ready-for-agent` is `#31` (`Frontend piloto: bloco 0 de autenticação e sessão para SPA`)
