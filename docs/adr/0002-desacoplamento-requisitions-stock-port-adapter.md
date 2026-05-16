# ADR 0002 — Desacoplamento requisitions → stock via Port/Adapter

## Status

Aceita.

## Contexto

O módulo `requisitions` possui 6 chamadas diretas a `apps.stock.services.*` e `apps.stock.models.EstoqueMaterial` dentro de `requisitions/services.py`, criando acoplamento ponto-a-ponto entre os dois módulos.

As operações de estoque afetadas são:

| Função de serviço | Chamadas a stock |
|---|---|
| `autorizar_requisicao` | `registrar_reserva_por_autorizacao` (via side effect na tabela de transições) |
| `_cancelar_autorizada_sem_saldo` | `_travar_estoques_dos_itens` → `EstoqueMaterial.select_for_update()` + `registrar_liberacao_reserva_por_atendimento` (via side effect) |
| `retirar_requisicao` | `_travar_estoques_dos_itens` + `registrar_saida_por_atendimento` + `registrar_liberacao_reserva_por_atendimento` (direto) |

Todas as mutações de estoque ocorrem dentro de blocos `transaction.atomic()` e exigem `select_for_update()` para garantir consistência. Uma falha de estoque deve causar rollback da transição de status da requisição — invariante crítico.

Duas opções foram avaliadas:

**A — Eventos de domínio com subscriber em stock**
`requisitions` publica eventos; `stock` subscreve e aplica as mutações.

**B — Port/Adapter (`StockPort`)**
`requisitions` define interface `StockPort` (Protocol). `stock` implementa o adapter. Serviços recebem o port por injeção com default.

## Decisão

Adotada a **Opção B — Port/Adapter**.

### Por que Option A foi rejeitada

O event bus existente em `core/events.py` possui dois comportamentos incompatíveis com a garantia transacional exigida:

- `publish()` silencia exceções de subscribers (`except Exception: logger.exception(...)`). Uma falha de estoque não faz rollback da transição de requisição.
- `publish_on_commit()` dispara pós-commit via `transaction.on_commit`. Rollback já não é possível após o commit.

Corrigir Option A exigiria bifurcar o bus com um terceiro modo (`publish_sync_raising`) que propaga exceções e roda inline na transação. Isso transformaria uma ferramenta de notificação em orquestradora de operações críticas — complexidade acidental sem benefício.

### Decisões de design do Port/Adapter

**Localização**
- `StockPort` (Protocol): `apps/requisitions/ports.py`
- `StockAdapter` (implementação): `apps/stock/adapters.py`

A fronteira de dependência segue a regra do consumidor: `requisitions` define o contrato, `stock` implementa. Com `typing.Protocol`, `StockAdapter` satisfaz o port por duck typing estrutural — sem importação explícita de `requisitions` dentro de `stock`.

**Granularidade do port**
Três métodos coarse-grained, um por evento de negócio que toca estoque. Nenhum handle opaco (`EstoqueMaterial`) vaza para `requisitions`.

```python
# apps/requisitions/ports.py
from typing import Protocol
from apps.requisitions.models import ItemRequisicao, Requisicao


class StockPort(Protocol):
    def aplicar_reservas_autorizacao(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...

    def liberar_reservas_cancelamento(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...
    # Encapsula: lock de estoques → verificação de saldo_fisico
    # → DomainConflict se saldo > 0 → liberação de reservas.
    # A regra "não cancela se há saldo físico" permanece sob controle
    # do adapter, que possui o contexto transacional e o lock.

    def aplicar_saidas_e_liberacoes_retirada(
        self,
        requisicao: Requisicao,
        itens_autorizados: list[ItemRequisicao],
    ) -> None: ...
    # Encapsula: lock de estoques → saída para itens entregues
    # → liberação de reserva para itens não entregues.
```

**Side effects na tabela de transições**
As funções `_side_effect_reservar_itens_autorizados` e `_side_effect_liberar_reservas_cancelamento` são removidas de `TRANSICOES_REQUISICAO`. As chamadas ao port passam a ser explícitas nas funções públicas de serviço, após `_apply_requisicao_transition`. A máquina de estados fica responsável apenas por: mudança de status, campos de auditoria, timeline e notificações.

**Injeção de dependência**
Parâmetro com default — as views DRF não precisam mudar:

```python
_default_stock: StockPort = StockAdapter()

def autorizar_requisicao(
    *,
    requisicao: Requisicao,
    ator: User,
    itens: list[ItemAutorizacaoData],
    stock: StockPort = _default_stock,
) -> Requisicao: ...
```

`StockAdapter` é stateless. Instância única no módulo é segura.

**Testabilidade**
Testes de `requisitions` recebem `StubStockPort` (spy) via parâmetro — sem `mock.patch`, sem acesso ao DB de estoque:

```python
class StubStockPort:
    def __init__(self):
        self.reservas_aplicadas: list = []
        self.cancelamentos_liberados: list = []
        self.retiradas_aplicadas: list = []
        self.deve_falhar_em: str | None = None  # nome do método

    def aplicar_reservas_autorizacao(self, requisicao, itens_autorizados):
        if self.deve_falhar_em == "aplicar_reservas_autorizacao":
            raise DomainConflict("stub: falha simulada")
        self.reservas_aplicadas.append((requisicao, itens_autorizados))

    def liberar_reservas_cancelamento(self, requisicao, itens_autorizados):
        if self.deve_falhar_em == "liberar_reservas_cancelamento":
            raise DomainConflict("stub: falha simulada")
        self.cancelamentos_liberados.append((requisicao, itens_autorizados))

    def aplicar_saidas_e_liberacoes_retirada(self, requisicao, itens_autorizados):
        if self.deve_falhar_em == "aplicar_saidas_e_liberacoes_retirada":
            raise DomainConflict("stub: falha simulada")
        self.retiradas_aplicadas.append((requisicao, itens_autorizados))
```

Testes de lógica de estoque (`tests/stock/`) continuam como integration tests com DB real.

## Consequências

### Positivas

- `requisitions` não importa mais nada de `apps.stock` — acoplamento eliminado.
- Falha de estoque propaga exceção dentro do `atomic()` → rollback garantido.
- Testes de requisition ficam isolados de `EstoqueMaterial` e `MovimentacaoEstoque`.
- `StubStockPort` permite testar cenários de falha de estoque sem infraestrutura.
- Máquina de estados (`TRANSICOES_REQUISICAO`) fica coesa: só estado, auditoria e notificações.

### Negativas / Custos

- Três funções de serviço ganham parâmetro adicional (`stock`).
- `StockAdapter` concentra lock + validação de domínio (`saldo_fisico`) de um ponto de negócio (`cancelar_autorizada_sem_saldo`). A regra sai do service e vai para o adapter.
- Testes existentes de `requisitions` que dependem de `EstoqueMaterial` precisam ser convertidos para usar `StubStockPort`.

## Alternativas consideradas

### Option A — Eventos de domínio com subscriber em stock

Rejeitada. O event bus atual silencia exceções e não suporta semântica transacional. Corrigir exigiria bifurcar o bus em dois modos de comportamento, introduzindo complexidade sem benefício arquitetural real. O bus permanece como ferramenta de notificação.

### Port/Adapter fine-grained (espelha funções atuais, 4 métodos)

Considerado. Rejeitado porque vaza `EstoqueMaterial` como handle opaco para `requisitions`, mantendo acoplamento implícito ao modelo de stock.

### Variável de módulo com monkey-patch em testes

Considerado. Rejeitado em favor de parâmetro com default — mais explícito, sem dependência de `mock.patch` e compatível com tipagem estática.

## Issue relacionada

Desbloqueada por: #11 (máquina de estados declarativa estável).
Desbloqueia: #5 (implementar costura requisitions → stock).
