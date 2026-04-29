# Users, sectors, and permission foundation

Updated on 2026-04-27 after merging PRs through PIL-BE-ACE-003.

## Domain pieces now in place
- Custom `User` model authenticated by `matricula_funcional`
- `MatriculaBackend` registered in Django authentication backends for session/admin login by matrícula
- `Setor` model with `nome`, `chefe_responsavel`, `is_active`, timestamps
- `User.setor` as protected FK for the user's main sector
- `User.papel` using `PapelChoices` with default `solicitante`
- Canonical constant `SETOR_NOME_ALMOXARIFADO = "Almoxarifado"`

## Important invariants implemented
- Sector must have a chief
- A chief cannot manage two sectors
- Sector name is unique
- Users protect sector deletion (`on_delete=PROTECT`)
- `Setor.clean()` enforces that `chefe_responsavel` belongs to that sector
- Chief-of-sector contextual scope depends on `setor_responsavel`, not just `User.setor`
- Chief of warehouse can authorize only the canonical Almoxarifado sector, not any sector matching their current allocation

## Policy surface in `apps/users/policies.py`
- `pode_criar_requisicao_para(criador, beneficiario)`
- `pode_autorizar_setor(autorizador, setor)`
- `pode_ver_fila_atendimento(user)`
- `pode_operar_estoque(user)` for common warehouse operations
- `pode_operar_estoque_chefia(user)` for chief-only warehouse actions

## Usage guidance
- Reuse these policy helpers from both services and views (PER-08)
- Do not infer chief powers from role alone when the rule depends on the responsible sector
- When authorizing warehouse requests, use the canonical Almoxarifado constant instead of duplicating the literal string in services/views/tests
- Keep serializer/admin checks non-authoritative; critical contextual authorization belongs in shared policies and service revalidation

## Test posture
- Model/domain tests distinguish user-facing validation from DB-level integrity enforcement
- Policy tests cover both positive and negative role/scope cases, including warehouse-chief regressions
- Authentication coverage must include inactive-user denial plus the real Django auth path (`authenticate(username=..., password=...)`) so matricula login remains compatible with admin/session flows
