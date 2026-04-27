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
- Autorização contextual deve estar em `policies.py` ou módulo equivalente, compartilhado por views e services
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

## 2. Registros históricos e ledgers auditáveis

- Registros históricos, lançamentos de ledger e trilhas auditáveis são **imutáveis**
- Nunca devem ser editados, deletados ou sobrescritos após criação
- Correções devem ser feitas criando um novo lançamento compensatório, mantendo o histórico original preservado

Exemplo de boa prática: se um lançamento de saída foi registrado incorretamente, criar um lançamento de estorno/correção com referência ao original, em vez de alterar o registro já auditado.

❌ Qualquer tentativa de:
- update
- delete
- sobrescrita de registro histórico

➡️ deve ser tratada como **erro crítico**

---

## 3. Consistência transacional de saldos e reservas

Toda operação que altera saldo, reserva, disponibilidade ou posição contábil deve:

- usar `transaction.atomic()`
- usar locking (`select_for_update()`) na linha agregadora que representa o saldo atual
- adquirir locks em ordem determinística quando envolver múltiplos objetos
- garantir consistência entre:
  - saldo atual persistido
  - lançamento histórico/ledger
  - saldo posterior registrado para auditoria

❌ Não pode existir:
- dupla baixa/processamento duplicado
- saldo negativo indevido
- race condition
- divergência entre ledger e saldo atual

---

## 4. Snapshot histórico é obrigatório

- Campos de rastreabilidade usados em decisões, auditoria ou relatórios devem ser copiados como **snapshot histórico** no momento da criação
- Snapshots nunca devem ser recalculados a partir de cadastros mutáveis

❌ Não pode:
- buscar dinamicamente dados atuais de usuário, setor, perfil, centro de custo ou escopo para explicar uma decisão passada
- atualizar snapshot histórico após persistência, salvo correção auditada e explicitamente modelada

➡️ isso quebraria rastreabilidade

---

## 5. Notificações NÃO são domínio

- Notificações, e-mails, webhooks e integrações externas são **side effects**
- Side effects nunca são fonte de verdade

❌ Não pode:
- conter regra de negócio
- controlar fluxo do sistema
- ser pré-condição para sucesso de operação

➡️ falha de side effect não deve quebrar a operação principal

➡️ Comunicação entre domínio e side effects deve ser feita por eventos pós-commit, por exemplo via `core/events.py` (`subscribe()` + `publish_on_commit()`). Imports diretos que acoplam domínio a notificações, e-mail, webhooks ou integrações externas são violação de arquitetura.

---

## 6. Direção de dependências entre apps

Regras:

- dependências entre apps de domínio devem ser unidirecionais e explícitas
- apps de side effect não devem controlar nem importar fluxos críticos de domínio
- comunicação com side effects deve ocorrer por evento pós-commit via `core/events.py`
- shared code deve ficar em módulos estáveis e sem dependência de domínio específico

❌ Evitar:
- import circular
- acoplamento cruzado
- dependência direta de domínio para infraestrutura opcional

---

## Operações críticas

### Concorrência e idempotência

Cenários críticos:

- dupla execução da mesma transição de estado
- retry de chamada HTTP ou job assíncrono
- execução simultânea de actions administrativas ou endpoints

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
