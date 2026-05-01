# Requisitions authorization and fulfillment workflow

Updated on 2026-05-01 after merge of PR #25.

## Scope landed
- `PIL-BE-REQ-002`: annual public numbering on first submission for authorization
- `PIL-BE-REQ-003`: draft request creation API
- `PIL-BE-REQ-004`: create for self or third party according to role/scope
- `PIL-BE-REQ-005`: submit draft for authorization
- `PIL-BE-REQ-007`: return pending request to draft
- `PIL-BE-REQ-008`: discard/cancel before authorization
- `PIL-BE-AUT-001`: pending-approvals listing
- `PIL-BE-AUT-003`: authorization total/partial write path
- `PIL-BE-AUT-004`: full-request refusal
- `PIL-BE-AUT-005`: reservation movement on authorization
- `PIL-BE-AUT-006`: balance revalidation and locking during authorization
- `PIL-BE-ATE-001`: pending-fulfillments listing
- `PIL-BE-ATE-003`: full fulfillment write path
- `PIL-BE-ATE-006`: withdrawal metadata on fulfillment

## Public API now exposed
Under `/api/v1/requisitions/`:
- `POST /` create draft
- `POST /{id}/submit/`
- `POST /{id}/return-to-draft/`
- `DELETE /{id}/discard/`
- `POST /{id}/cancel/`
- `GET /pending-approvals/`
- `POST /{id}/authorize/`
- `POST /{id}/refuse/`
- `GET /pending-fulfillments/`
- `POST /{id}/fulfill/`

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
- Authorization is applied through a declarative transition table plus a single applier function, not scattered inline state changes.
- Authorization payload cannot repeat `item_id`.
- Partial or zero authorization requires non-blank trimmed `justificativa_autorizacao_parcial`.
- Authorization must leave at least one item with quantity greater than zero.
- Permission/object-scope checks for authorize/refuse run in services against the `select_for_update()`-locked requisition instance.
- Successful authorization persists `quantidade_autorizada` per item, records `AUTORIZACAO_TOTAL` or `AUTORIZACAO_PARCIAL`, and triggers `RESERVA_POR_AUTORIZACAO` movements that increase `saldo_reservado` without changing `saldo_fisico`.
- Reservation service itself rejects `quantidade <= 0` and revalidates `quantidade <= saldo_disponivel` after locking stock rows.
- Full refusal requires trimmed non-blank `motivo_recusa`, records `RECUSA`, and does not reserve stock.
- Pending-fulfillments is intentionally global for Almoxarifado roles because `docs/design-acesso-rapido/matriz-permissoes.md` says Almoxarifado can see requests from all sectors and the fulfillment queue.
- Full fulfillment currently has no partial/zero-delivery variant: every positive authorized item is delivered with `quantidade_entregue = quantidade_autorizada`.
- Fulfillment writes must call object-aware `pode_atender_requisicao(ator, requisicao)` against the locked/reloaded requisition, not only global queue/stock role helpers.
- Full fulfillment transitions `autorizada` to `atendida`, records `ATENDIMENTO`, persists `responsavel_atendimento`, `data_finalizacao`, `retirante_fisico`, and optional trimmed `observacao_atendimento`.
- `SAIDA_POR_ATENDIMENTO` decrements both `saldo_fisico` and `saldo_reservado`; the stock service rejects non-positive quantity, insufficient physical stock, and insufficient reserved stock after locking.

## Validation / contract posture
- Serializer input fails fast for empty `itens` list.
- Authorization serializer rejects negative `quantidade_autorizada` and duplicate `item_id`.
- Domain/state conflicts return HTTP 409 with code `domain_conflict`.
- Error envelope must always include `trace_id`.
- OpenAPI test coverage must assert every requisitions action route added in this slice.
- Service-level tests must cover happy path, refusal, partial/zero justification rule, stale-balance conflict, and concurrent authorization on the same stock.
- Fulfillment service/API tests must cover happy path, object-aware permission denial, insufficient `saldo_fisico`, insufficient `saldo_reservado`, idempotency/domain conflicts, and no-side-effect behavior on failure.

## Timeline / audit decisions
- No timeline event on draft creation.
- Timeline starts on formalization with `ENVIO_AUTORIZACAO`.
- Re-submit records `REENVIO_AUTORIZACAO`.
- Return to draft records `RETORNO_RASCUNHO`.
- Pre-authorization cancel records `CANCELAMENTO`.
- Authorization records `AUTORIZACAO_TOTAL` or `AUTORIZACAO_PARCIAL`.
- Refusal records `RECUSA`.
- Full fulfillment records `ATENDIMENTO`.

## Validation commands proven in this slice
For schema/model changes, the correct local flow is:
1. `rtk make init` for initial environment bootstrap only
2. `rtk make setup` to rebuild ephemeral migrations and local DB state
3. run targeted pytest or `rtk make test`

A useful targeted validation snapshot for the merged authorization slice is:
- `rtk pytest tests/requisitions/test_api.py tests/requisitions/test_services.py tests/stock/test_services_estoque.py tests/test_api_schema.py`
- after the hardening follow-up, `rtk pytest tests/requisitions/test_services.py tests/stock/test_services_estoque.py`
- lint for touched files with `rtk ruff check ...` when changing requisition/stock services or tests

A useful targeted validation snapshot for the merged fulfillment slice is:
- `rtk pytest tests/requisitions/test_api.py tests/requisitions/test_services.py tests/stock/test_services_estoque.py`
- `rtk pytest tests/test_api_schema.py::TestOpenAPISchema::test_schema_contem_rotas_de_requisicoes`
- `rtk ruff check apps/requisitions/policies.py apps/requisitions/serializers.py apps/requisitions/services.py apps/requisitions/views.py apps/stock/services.py tests/requisitions/test_api.py tests/requisitions/test_services.py tests/stock/test_services_estoque.py tests/test_api_schema.py`

Next workflow frontier:
- partial / zero fulfillment semantics and per-item justification
- reservation release for undelivered quantities
- authorized-request cancellation after reservation
- return / estorno / exceptional stock-exit flows with a canonical lock acquisition order
