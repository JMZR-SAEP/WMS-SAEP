# AGENTS.md

## Projeto

ERP auxiliar para o **SAEP — Serviço de Água e Esgoto de Pirassununga**, autarquia municipal. O foco inicial é um backend robusto em **Django + Django REST Framework (DRF)**.

Use as ferramentas MCP do Serena para **TODAS** operações de código neste repositório — exploração, leitura e edição. Leia e siga as `initial_instructions`, as instruções do próprio Serena.

Para revisão de código, considerar também `docs/code-review-guidelines.md`, que define invariantes obrigatórios do sistema e orienta o comportamento de reviews.

Para contratos de API DRF, seguir `docs/design-acesso-rapido/api-contracts.md`, que define o padrão obrigatório para autenticação, autorização, serializers de entrada/saída, status HTTP, envelope de erro, paginação/filtros e schema OpenAPI.

Para invariantes críticos de domínio, seguir `docs/design-acesso-rapido/matriz-invariantes.md`, que consolida regra de negócio, camada de implementação esperada, reforços e testes obrigatórios.

Para permissões, escopos e papéis, seguir `docs/design-acesso-rapido/matriz-permissoes.md`, que consolida a referência canônica para `policies.py`, services, endpoints DRF e testes de autorização.

## Estratégia de leitura da documentação

Para economizar tokens e manter os agentes focados, a documentação está dividida por frequência de uso:

- `docs/design-acesso-rapido/`: sínteses operacionais. Deve ser a primeira fonte consultada por agentes de IA.
- `docs/design-acesso-ocasional/`: documentação completa. Deve ser consultada apenas quando a síntese rápida não resolver a dúvida, quando houver ambiguidade ou quando a tarefa depender de detalhe de domínio.

Leitura padrão antes de implementar:

- `docs/design-acesso-rapido/stack.md`, para decisões técnicas e stack;
- `docs/design-acesso-rapido/api-contracts.md`, para contratos DRF;
- `docs/design-acesso-rapido/matriz-invariantes.md`, para invariantes críticos de domínio, camada esperada e testes obrigatórios;
- `docs/design-acesso-rapido/matriz-permissoes.md`, para papéis, escopos, permissões e testes de autorização;
- `docs/design-acesso-rapido/estado-transicoes-requisicao.md`, para ciclo de vida de requisições.

Consultar `docs/design-acesso-ocasional/` quando as matrizes de invariantes/permissões e as demais sínteses rápidas não resolverem a dúvida, ou quando a tarefa envolver regra detalhada de domínio, permissões, estoque, requisições, importação SCPI, critérios de aceite, conflito documental ou decisão que precise ser explicada em PR.

Em caso de conflito entre síntese e documentação completa, prevalece `docs/design-acesso-ocasional/`, salvo decisão posterior registrada. Mudanças de regra de negócio devem atualizar a documentação rápida e a documentação completa quando ambas forem afetadas.

## Ambiente de desenvolvimento efêmero

Durante a fase inicial, o ambiente local é descartável.

- o banco local pode ser apagado e recriado;
- o fluxo padrão é resetar banco -> aplicar migrations -> carregar dados mínimos (quando existirem);
- migrations locais são não versionadas e ignoradas pelo `.gitignore`.
- `rtk make init` deve ser usado no setup inicial do projeto para criar `.venv` e instalar dependências.
- `rtk make setup` é o comando principal do ciclo efêmero: apaga migrations locais e recria tudo do zero.
- neste momento do projeto, toda edição de `models`/schema deve ser seguida de `rtk make setup`, para não depender de gestão manual de migrations.
- migrations de apps devem ser tratadas como artefato efêmero: antes de testar ou concluir uma implementação que altere schema, apagar e recriar as migrations locais do zero, simulando uma primeira execução limpa do app.
- confeccionar novos arquivos de migration não faz parte da entrega normal do trabalho neste contexto efêmero.
- a fonte de verdade para mudanças estruturais são `models`, constraints, índices, regras de domínio e testes; migrations locais servem apenas para materializar o banco local.
- tarefas sem mudança estrutural podem seguir fluxo incremental; reset completo é obrigatório apenas para mudanças de schema/model ou quando o ambiente local estiver inconsistente.
- todos os comandos shell e `make` devem ser chamados com prefixo `rtk`, usando `rtk proxy` apenas quando `rtk` não suportar a forma necessária.

## Comandos gerais

Rotinas principais do projeto via `rtk make`:

- `rtk make help`: lista as rotinas disponíveis;
- `rtk make prepare`: materializa `.env` a partir de `.env.example`;
- `rtk make init`: bootstrap inicial (uma vez por ambiente) para criar/recriar o ambiente Python e instalar dependências com `uv sync`;
- `rtk make setup`: comando principal do desenvolvimento efêmero; limpa o ambiente, apaga/recria schema+migrations locais e coleta estáticos; usar sempre após editar `models`/schema;
- `rtk make clean`: remove caches e artefatos locais sem afetar o banco;
- `rtk make cleanall`: executa limpeza local e reseta o schema `public` do PostgreSQL;
- `rtk make veryclean`: remove `.venv`, caches e migrations locais geradas;
- `rtk make resetpostgres`: apaga e recria o schema `public` usando `DATABASE_URL`;
- `rtk make test`: executa a suíte com `config.settings.test`;
- `rtk make run`: sobe o servidor Django com `config.settings.dev`;
- `rtk make resetdb`: reaplica migrations no banco atual sem apagar arquivos de migration.

## Guardrails Para o Projeto

### Faça

- Declare em todo endpoint: autenticação, autorização, entrada, saída, status HTTP, envelope de erro, paginação/filtros e schema OpenAPI.
- Siga `docs/design-acesso-rapido/api-contracts.md` como contrato canônico para endpoints DRF.
- Centralize regras de autorização contextual em `policies.py` ou equivalente.
- Faça views e services chamarem a mesma política de autorização.
- Valide perfil e escopo do objeto no service para toda escrita.
- Mantenha regras de negócio em services.
- Use uma máquina de estados declarativa, com tabela de transições e uma única função aplicadora.
- Mantenha uma única fonte de verdade para aprovação, status, saldo, entrega e auditoria.
- Proteja campos snapshot/históricos contra alteração após criação.
- Reforce invariantes críticos com constraints, triggers, managers ou testes de bypass.
- Use `transaction.atomic()`, `select_for_update()` e ordem determinística de locks em mutações de saldo ou ledger.
- Rode testes PostgreSQL na CI para locking, constraints, índices parciais e concorrência.
- Gere e compare o schema OpenAPI na CI.
- Use `publish_on_commit()` para side effects pós-transação.
- Adicione teste de regressão para todo bug corrigido.
- Cubra regra crítica com caminho feliz, permissão negada, violação de domínio e contrato de erro.

### Não Faça

- Não deixe contrato HTTP para “arrumar depois”.
- Não exponha endpoint sem contrato explícito de entrada, saída, erros e permissões.
- Não duplique regra de autorização entre view, service e serializer.
- Não confie só em `permission_classes` quando a regra depende do objeto ou departamento.
- Não coloque regra de negócio em views, serializers, admin actions, signals ou management commands.
- Não crie caminhos paralelos que gravem o mesmo estado de formas diferentes.
- Não implemente transições de status com `if/elif` espalhado por várias funções.
- Não trate código existente como fonte de verdade quando ele conflitar com documentação ou invariantes.
- Não deixe campo histórico/snapshot ser recalculado ou atualizado depois da criação.
- Não dependa só de `save()`, `clean()` ou validação de serializer para invariantes críticos.
- Não assuma que testes em SQLite provam comportamento de PostgreSQL.
- Não altere saldo, ledger ou registros auditáveis sem transação e lock.
- Não faça notificações ou side effects decidirem o sucesso da operação principal.
- Não aceite mudança de contrato sem atualizar OpenAPI, testes e documentação.
- Não corrija bug sem adicionar teste que falharia antes da correção.

## GitHub Flow

- `main` sempre estável — nenhum commit direto
- Antes de implementar crie branches: `feat/{descricao-curta}`, `fix/{descricao-curta}`, `chore/{descricao-curta}`, `docs/{descricao-curta}`, `refactor/{descricao-curta}`, `test/{descricao-curta}`
- nomes de branch devem ser curtos, sem acentos, sem espaços e refletir uma única unidade de mudança
- evitar branches e PRs com escopo amplo demais; dividir trabalho extenso em fatias auditáveis
- Sempre que publicar um PR, preencha o `.github/pull_request_template.md` detalhadamente
- Quando houver divergência com `.serena/memories` ou ambiguidade de contrato, o PR deve explicitar a decisão tomada

### Commits pequenos e incrementais

Ao implementar uma tarefa, prefira fazer **commits pequenos, coesos e revisáveis** em vez de um único commit grande no final.

Diretrizes:

- Faça commits por unidade lógica de mudança.
- Cada commit deve deixar o projeto em um estado consistente.
- Evite misturar refactors, mudanças de modelo, migrations, testes e ajustes de documentação no mesmo commit quando puder separá-los.
- Rode os checks relevantes antes de cada commit ou, no mínimo, antes de finalizar a sequência.
- Use mensagens de commit descritivas, explicando o que mudou.
- Commits no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`, `docs:`)

Exemplos de bons commits:

feat(materials): add Material model
feat(stock): add EstoqueMaterial model
test(materials): cover Material validation
test(stock): cover available quantity calculation
docs: update pilot data modeling notes


## Code Review

- Revisões (automáticas ou manuais) devem seguir `docs/code-review-guidelines.md`.
- Em caso de conflito com sugestões genéricas, prevalecem os invariantes arquiteturais e de domínio documentados no projeto.
