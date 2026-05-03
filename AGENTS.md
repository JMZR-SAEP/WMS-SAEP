# AGENTS.md

## Agent skills

### Issue tracker

Issues for this repo live in GitHub Issues. Use `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Repo uses default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Repo is single-context. Read root `CONTEXT.md`, root `docs/adr/`, then `docs/design-acesso-rapido/` first and `docs/design-acesso-ocasional/` when need depth. See `docs/agents/domain.md`.

## Projeto

WMS auxiliar para o **SAEP — Serviço de Água e Esgoto de Pirassununga**, autarquia municipal. O projeto segue **backend/API-first** em **Django 6 + Django REST Framework (DRF)** e agora possui também uma frente ativa de frontend para o piloto, implementada como SPA separada no mesmo repositório.

## Estratégia de leitura da documentação

Para economizar tokens e manter os agentes focados, a documentação de design do projeto está dividida por frequência de uso:

- `docs/design-acesso-rapido/`: sínteses operacionais. Deve ser a primeira fonte consultada por agentes de IA.
- `docs/design-acesso-ocasional/`: documentação completa. Deve ser consultada apenas quando a síntese rápida não resolver a dúvida, quando houver ambiguidade ou quando a tarefa depender de detalhe de domínio.
- `docs/code-review-guidelines.md` e `.coderabbit.yaml`: orientam o comportamento de revisões de código.

### IDs do Context7 para consulta rápida:

- Django 6: `/django/django/6_0a1`
- DRF: `/websites/django-rest-framework`
- React Router / TanStack Router / TanStack Query / TanStack Table / openapi-typescript: consultar via Context7 quando a tarefa tocar a SPA do piloto

### Exemplos positivos do que fazer:

- Implementando ou alterando um `Model`: consultar documentação de Django Models, Fields, Meta options, constraints, indexes, managers e validação de modelos conforme a mudança.
- Implementando relacionamento entre entidades: consultar documentação de `ForeignKey`, `OneToOneField`, `ManyToManyField`, `on_delete`, `related_name`, constraints e comportamento de queries relacionadas.
- Implementando constraints ou índices: consultar documentação de `UniqueConstraint`, `CheckConstraint`, `Index`, índices condicionais/parciais quando aplicável e limitações do banco usado pelo projeto.
- Implementando transações ou mutações críticas de saldo/estoque: consultar documentação de `transaction.atomic()`, `select_for_update()`, comportamento transacional e locking no Django.
- Implementando DRF Serializer: consultar documentação de Serializers, ModelSerializer, validação por campo, validação de objeto, campos read-only/write-only e representação de erros.
- Implementando ViewSet/APIView: consultar documentação de DRF ViewSets, Generic Views, Mixins, Routers, status codes, permissions, authentication e paginação/filtros quando aplicável.
- Implementando autorização: consultar documentação de DRF Permissions e autenticação, além das políticas internas do projeto em `policies.py` ou equivalente.
- Implementando filtros, busca ou ordenação: consultar documentação de DRF Filtering, Django QuerySet API, lookup expressions e performance de queries.
- Implementando endpoint com upload/download, arquivos ou campos especiais: consultar documentação específica de parsers, renderers, FileField/ImageField e tratamento de request/response no DRF.
- Implementando testes: consultar documentação de Django TestCase/TransactionTestCase, pytest quando usado no projeto, DRF APIClient/APIRequestFactory e ferramentas adequadas para o tipo de comportamento testado.
- Alterando comandos de management, signals, admin ou settings: consultar a documentação específica da área alterada antes de editar.
- Implementando a SPA do piloto: consultar `docs/design-acesso-rapido/frontend-arquitetura-piloto.md`, o ADR do frontend e a documentação atual das bibliotecas frontend envolvidas via Context7 antes de fechar a solução.
- Antes de concluir, conferir se a implementação continua alinhada com a documentação consultada, com `docs/design-acesso-rapido/` e com os guardrails deste arquivo.

### Exemplos negativos do que **não** fazer:

- Não implementar ou alterar código Django/DRF usando apenas memória, conhecimento prévio ou tentativa e erro sem consultar o Context7.
- Não procurar documentação genérica quando a tarefa exige documentação específica. Exemplo: ao alterar um `ModelViewSet`, não consultar apenas documentação geral de Django; consulte DRF ViewSets, Routers, Serializers e Permissions conforme o caso.
- Não assumir APIs, parâmetros ou comportamentos de bibliotecas sem confirmar na documentação atual. Exemplo: não inventar argumentos de `Serializer`, `QuerySet`, `transaction.atomic()` ou `select_for_update()`.
- Não copiar padrões de código existente se houver dúvida sobre compatibilidade com a versão atual das bibliotecas; confirme com Context7 antes.
- Não usar posts de blog, respostas antigas, snippets aleatórios ou conhecimento desatualizado como fonte principal quando houver documentação oficial disponível via Context7.
- Não fazer uma implementação ampla e só consultar documentação depois que os testes falharem; consulte a documentação antes de definir a solução.
- Não ignorar documentação de segurança, autenticação, autorização, transações, validação ou concorrência quando a mudança tocar esses temas.
- Não misturar conceitos de versões diferentes do Django, DRF ou bibliotecas relacionadas sem validar a versão usada pelo projeto.
- Não iniciar features operacionais da SPA antes da conclusão do bloco 0 de APIs habilitadoras do backend definido em `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` e no backlog do piloto.

## Ambiente de desenvolvimento efêmero

Durante a fase inicial, o ambiente local é descartável.

- o banco local pode ser apagado e recriado;
- o fluxo padrão é resetar banco -> aplicar migrations -> carregar dados mínimos (quando existirem);
- migrations locais são não versionadas e ignoradas pelo `.gitignore`.
- `rtk make init` deve ser usado no setup inicial do projeto para criar `.venv` e instalar dependências.
- `rtk make setup` é o comando principal do ciclo efêmero: apaga migrations locais e recria tudo do zero.
- `rtk make test` executa a suíte com `config.settings.test`;
- neste momento do projeto, toda edição de `models`/schema deve ser seguida de `rtk make setup`, para não depender de gestão manual de migrations.
- migrations de apps devem ser tratadas como artefato efêmero: antes de testar ou concluir uma implementação que altere schema, apagar e recriar as migrations locais do zero, simulando uma primeira execução limpa do app.
- confeccionar novos arquivos de migration não faz parte da entrega normal do trabalho neste contexto efêmero.
- a fonte de verdade para mudanças estruturais são `models`, constraints, índices, regras de domínio e testes; migrations locais servem apenas para materializar o banco local.
- tarefas sem mudança estrutural podem seguir fluxo incremental; reset completo é obrigatório apenas para mudanças de schema/model ou quando o ambiente local estiver inconsistente.
- todos os comandos shell e `make` devem ser chamados com prefixo `rtk`, usando `rtk proxy` apenas quando `rtk` não suportar a forma necessária.

## Guardrails Para o Projeto

### Faça

- Declare em todo endpoint: autenticação, autorização, entrada, saída, status HTTP, envelope de erro, paginação/filtros e schema OpenAPI.
- Siga `docs/design-acesso-rapido/api-contracts.md` como contrato canônico para endpoints DRF.
- Siga `docs/design-acesso-rapido/frontend-arquitetura-piloto.md` como contrato canônico para a arquitetura da SPA do piloto.
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
- Trate o OpenAPI exportado como contrato vivo entre backend e frontend.
- Use `publish_on_commit()` para side effects pós-transação.
- Adicione teste de regressão para todo bug corrigido.
- Cubra regra crítica com caminho feliz, permissão negada, violação de domínio e contrato de erro.

### Não Faça

- Não deixe contrato HTTP para “arrumar depois”.
- Não exponha endpoint sem contrato explícito de entrada, saída, erros e permissões.
- Não acople a SPA do piloto ao admin do Django, a templates server-rendered ou a superfícies implícitas de autenticação.
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
- Não implemente frontend do piloto em desacordo com o ADR macro e o guia operacional do frontend.
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
