# Requisitions pre-authorization workflow

Updated on 2026-04-30 after merge of PR #23.

## Scope landed
- `PIL-BE-REQ-002`: annual public numbering on first submission for authorization
- `PIL-BE-REQ-003`: draft request creation API
- `PIL-BE-REQ-004`: create for self or third party according to role/scope
- `PIL-BE-REQ-005`: submit draft for authorization
- `PIL-BE-REQ-007`: return pending request to draft
- `PIL-BE-REQ-008`: discard/cancel before authorization
- `PIL-BE-AUT-001`: pending-approvals listing only; no authorize action yet

## Public API now exposed
Under `/api/v1/requisitions/`:
- `POST /` create draft
- `POST /{id}/submit/`
- `POST /{id}/return-to-draft/`
- `DELETE /{id}/discard/`
- `POST /{id}/cancel/`
- `GET /pending-approvals/`

View layer is a thin `RequisicaoViewSet`; domain rules live in `apps/requisitions/services.py`; contextual authz lives in `apps/requisitions/policies.py` and reuses `apps/users/policies.py`.

## Important domain decisions
- `numero_publico` is assigned only on the first submit to authorization, never on draft creation.
- Public number format is `REQ-AAAA-NNNNNN` and generation is concurrency-safe via `transaction.atomic()` + `select_for_update()` on the annual sequence row.
- Re-submit after return to draft preserves the existing public number.
- Drafts may temporarily exist with `status=rascunho` and `numero_publico` filled only when they were already formally submitted once and later returned to draft.
- If `data_envio_autorizacao` is filled, `numero_publico` is mandatory at DB level.
- Draft discard is physical delete only for a request never formalized (`numero_publico` absent and `data_envio_autorizacao` null).
- Cancel is logical and allowed for formalized draft or pending-authorization request; discard and cancel are different operations.
- Pending-approvals policy/queryset must return only `aguardando_autorizacao` rows in the caller's authorization scope.
- Request sector always comes from the beneficiary, never from the creator.
- No stock reservation, stock decrement, or warehouse movement happens in this slice.

## Validation / contract posture
- Serializer input now fails fast for empty `itens` list.
- Domain/state conflicts return HTTP 409 with code `domain_conflict`.
- Error envelope must always include `trace_id`.
- OpenAPI test coverage must assert every requisitions action route added in this slice.

## Timeline / audit decisions
- No timeline event on draft creation.
- Timeline starts on formalization with `ENVIO_AUTORIZACAO`.
- Re-submit records `REENVIO_AUTORIZACAO`.
- Return to draft records `RETORNO_RASCUNHO`.
- Pre-authorization cancel records `CANCELAMENTO`.

## Validation commands proven in this slice
For schema/model changes, the correct local flow is:
1. `rtk make init` for initial environment bootstrap only
2. `rtk make setup` to rebuild ephemeral migrations and local DB state
3. run targeted pytest or `rtk make test`

A partial validation snapshot for this merged slice was:
- requisitions tests passing locally
- schema route assertion for requisitions passing locally
- unrelated Swagger UI HTML rendering tests remained a separate environment issue and were not part of the requisitions domain behavior
