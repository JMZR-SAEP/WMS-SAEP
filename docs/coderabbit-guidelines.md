# CodeRabbit Guidelines — ERP-SAEP

Este documento define **invariantes arquiteturais e regras críticas de domínio** que DEVEM ser respeitadas em qualquer Pull Request.

O objetivo é orientar o CodeRabbit a fazer revisões alinhadas com o contexto real do sistema, evitando sugestões genéricas ou incorretas.

---

# 🧪 Contexto de desenvolvimento (IMPORTANTE)

## Ambiente efêmero (dev local)

O banco de dados local é descartável — o fluxo padrão é resetar e reaplicar migrations do zero.

### Implicações para review

Migrations são artefatos locais de setup — **não commitar, não rastrear, não exigir em PR**.
A regra `.gitignore` `apps/**/migrations/*.py` exclui todos os arquivos de migration do versionamento.

❌ Não sugerir: editar migrations existentes, commitar migrations, exigir backward compatibility de banco em dev.

⚠️ Exceção: staging/produção têm persistência real — mudanças destrutivas de schema devem ser **explicitadas no PR** nesses contextos.

Ao revisar mudança de schema em dev efêmero, priorizar: correção do model, constraints/índices no código-fonte, cobertura de testes.

---

# 🔒 Invariantes do Sistema (NUNCA QUEBRAR)

## 1. Regra de negócio centralizada

- Toda regra de negócio deve estar em `services.py`
- Isso inclui:
  - validações de domínio
  - autorização contextual (por perfil/setor)
  - transições de estado
  - efeitos colaterais
  - controle transacional

❌ NÃO colocar em:
- `views.py`
- `serializers.py`
- `models.py`
- `signals.py`
- managers ou helpers genéricos

---

## 2. Imutabilidade do estoque

- `StockMovement` é **imutável**
- Nunca pode ser editado ou deletado
- Correções são feitas criando um novo movimento do tipo `RETURN` (estorno)

Tipos de movimento válidos: `ENTRY` (entrada), `EXIT` (saída), `ADJUSTMENT` (ajuste), `RETURN` (estorno).

❌ Qualquer tentativa de:
- update
- delete
- sobrescrita de movimento

➡️ deve ser tratada como **erro crítico**

---

## 3. Consistência transacional de estoque

Toda operação que altera estoque deve:

- usar `transaction.atomic()`
- usar locking (`select_for_update`) na linha de `Stock`
- garantir consistência entre:
  - `Stock.quantity`
  - `StockMovement.balance_after`

❌ Não pode existir:
- dupla baixa
- saldo negativo indevido
- race condition
- divergência entre movimento e saldo

---

## 4. Snapshot histórico é obrigatório

- `MaterialRequest.department` é um **snapshot histórico**
- Nunca deve ser recalculado

❌ Não pode:
- usar `requester.department` dinamicamente após criação
- atualizar o campo após persistência

➡️ isso quebraria rastreabilidade

---

## 5. Notificações NÃO são domínio

- `notifications` é **side effect**
- nunca é fonte de verdade

❌ Não pode:
- conter regra de negócio
- controlar fluxo do sistema
- ser pré-condição para sucesso de operação

➡️ falha de notificação não deve quebrar a operação principal

➡️ Comunicação entre apps de domínio e `notifications` é feita via `core/events.py` (pub/sub in-process: `subscribe()` + `publish_on_commit()`). Imports diretos de apps de domínio para `notifications` são violação de arquitetura.

---

## 6. Direção de dependências entre apps

A arquitetura segue:

```
core → warehouse → movements → requisitions
                                     ↘
                                notifications
```

Regras:

- dependências são unidirecionais
- `notifications` não deve depender diretamente de apps de domínio
- comunicação deve ser por evento via `core/events.py`

❌ Evitar:
- import circular
- acoplamento cruzado

---

## Requisições

### Concorrência e idempotência

Cenários críticos:

- dupla entrega
- retry de request
- execução simultânea de actions

➡️ Deve existir proteção contra reprocessamento

---

# 📊 Auditoria e rastreabilidade

Toda ação relevante deve ser auditável:

- criação
- aprovação
- rejeição
- devolução
- cancelamento
- entrega
- ajuste
- estorno

➡️ Auditoria é implementada via `django-simple-history` nos models de domínio. Não sugerir logging manual ou signals de auditoria — o mecanismo já existe.

❌ Não aceitar:
- ações sem registro
- perda de histórico

---

# 🚫 Anti-padrões proibidos

No código:
- regra de negócio fora de `services.py`
- uso de signals para lógica crítica
- side effects silenciosos
- dependência circular entre apps
- uso de serializer como service layer

No review (CodeRabbit):
- sugerir "boas práticas" genéricas ignorando decisões arquiteturais explícitas
- sugerir abstrações desnecessárias sem problema concreto
- exigir migrations em contexto de dev efêmero

➡️ Reviews devem ser **context-aware**, não baseados em heurísticas genéricas

---

# 🧭 Diretriz final

O review DEVE priorizar: integridade de dados, consistência de fluxo, segurança e autorização, concorrência e atomicidade, aderência ao domínio.

Antes de sugerir qualquer mudança, validar:

1. Isso respeita as invariantes do domínio?
2. Isso considera o ambiente efêmero de desenvolvimento?
3. Isso resolve um problema real ou é apenas "boa prática" genérica?

Se a resposta para (3) for "boa prática genérica", a sugestão deve ser evitada. Qualquer desvio dos invariantes deve ser tratado como **alto risco**.
