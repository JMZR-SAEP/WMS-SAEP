# Backlog Técnico — Piloto Inicial

Este documento reúne apenas o escopo funcional do piloto inicial.

Para o backlog do MVP completo, consultar `docs/backlog/backlog-tecnico-mvp.md`.

## Pré-condição técnica obrigatória

Antes de iniciar qualquer tarefa `PIL-*`, executar completamente o backlog de materialização técnica em `docs/backlog/backlog-materializacao-django.md` (tarefas `MAT-000` a `MAT-006`).

As tarefas `MAT-*` são responsáveis por:
- Alinhar documentação pré-materialização (`MAT-000`)
- Inspecionar estrutura existente (`MAT-001`)
- Criar bootstrap Django mínimo (`MAT-002`)
- Configurar settings, ambiente e PostgreSQL (`MAT-003`)
- Configurar testes de smoke (`MAT-004`)
- Configurar DRF/OpenAPI/core API sem domínio (`MAT-005`)
- Ajustar CI genérica de bootstrap (`MAT-006`)

As tarefas `MAT-*` não fazem parte do domínio funcional do piloto. O backlog funcional do piloto começa em `PIL-BE-ACE-001`, que deve ser iniciado apenas após a materialização estar completa.

## 1. Estratégia de implementação

A implementação do ERP-SAEP deve ser organizada em três camadas de escopo:

1. **Piloto inicial**
   - Entrega mínima para validar o fluxo principal com usuários reais.
   - Deve focar em materiais de consumo cotidiano.
   - Deve manter controle em papel em paralelo.
   - Deve incluir apenas o necessário para criar requisição, autorizar, atender e baixar estoque.

2. **MVP completo**
   - Primeira versão operacional mínima após validação do piloto.
   - Inclui rotinas complementares, relatórios, devoluções, saídas excepcionais, estornos e gestão mais completa.

3. **Pós-MVP**
   - Funcionalidades explicitamente deixadas para versão futura.
   - Não devem ser implementadas antes da estabilização do MVP completo.

Princípios:

- Priorizar primeiro o fluxo essencial do piloto: criar requisição, autorizar, atender e baixar estoque.
- Implementar permissões desde o início, mesmo que nem todos os papéis usem todas as funcionalidades no piloto.
- Tratar o SCPI como fonte oficial dos dados cadastrais de materiais e de correções de saldo físico.
- Não implementar ajuste manual de estoque no MVP.
- Garantir rastreabilidade mínima desde o piloto.
- Evitar relatórios completos no piloto; usar apenas consultas operacionais necessárias.
- Não investir em frontend neste momento; priorizar domínio, API, autenticação, autorização e fluxos técnicos/administrativos.
- Manter o escopo do piloto menor que o MVP completo.
- Escrever tarefas pequenas o suficiente para serem executadas por agentes de IA com baixo risco de interpretação.
- Seguir a stack atual baseada em Django monolítico, Django REST Framework e PostgreSQL.
- Manter Celery fora do caminho crítico do piloto, deixando a importação CSV estruturada como serviço reutilizável.

Referências principais:

- `docs/design-acesso-ocasional/processos-almoxarifado.md`
- `docs/design-acesso-ocasional/modelo-dominio-regras.md`
- `docs/design-acesso-ocasional/importacao-scpi-csv.md`
- `docs/design-acesso-ocasional/mvp-plano-implantacao.md`
- `docs/design-acesso-ocasional/criterios-aceite.md`
- `docs/design-acesso-rapido/stack.md`

## 2. Convenção de tarefas para agentes de IA

Cada tarefa deve ser tratada como uma unidade de implementação independente, sempre que possível.

Formato recomendado de execução:

- **ID:** identificador rastreável da tarefa.
- **Fase:** Piloto inicial, MVP completo ou Pós-MVP.
- **Tipo:** Backend, API, Banco de dados, Testes, Documentação, Implantação ou Revisão.
- **Agente sugerido:** perfil de agente mais adequado para executar a tarefa.
- **Depende de:** tarefas que devem estar concluídas antes.
- **Objetivo:** resultado esperado da tarefa.
- **Regras de negócio:** regras que não podem ser violadas.
- **Entregáveis:** arquivos, endpoints, modelos, serviços, testes ou documentação esperados.
- **Testes esperados:** cenários mínimos que devem ser cobertos.
- **Critérios de aceite relacionados:** referência aos itens de `docs/design-acesso-ocasional/criterios-aceite.md`.

Orientações para agentes:

- Antes de implementar, ler os documentos de referência citados na tarefa.
- Não alterar regra de negócio sem atualizar também os critérios de aceite e os documentos de domínio/processo relacionados.
- Quando uma tarefa envolver status de requisição, preservar o ciclo de vida definido em `docs/design-acesso-ocasional/processos-almoxarifado.md`.
- Quando uma tarefa envolver estoque, preservar a separação entre saldo físico, saldo reservado e saldo disponível.
- Quando uma tarefa envolver material importado do SCPI, não permitir edição manual de dados cadastrais oficiais no ERP-SAEP.
- Toda implementação que altere estoque, status de requisição ou permissões deve possuir testes automatizados ou, no mínimo, cenários de validação documentados.
- Seguir as decisões técnicas registradas em `docs/design-acesso-rapido/stack.md`.
- Usar Django REST Framework para endpoints de API e manter views/serializers finos.
- Não abrir frente de implementação de frontend enquanto o foco do projeto permanecer em backend/API.

## 3. Épicos

1. **Base do sistema e permissões**
2. **Materiais, estoque e importação SCPI CSV**
3. **Requisições**
4. **Autorizações**
5. **Atendimento pelo Almoxarifado**
6. **Devoluções, saídas excepcionais e estornos**
7. **Notificações**
8. **Relatórios e painéis**
9. **Auditoria, histórico e rastreabilidade**
10. **Piloto e implantação gradual**

## 4. Backlog por fase de entrega

Observação de escopo atual:

- Tarefas identificadas como `FE` ou `fullstack`, bem como entregáveis descritos como telas, formulários ou componentes visuais, devem ser tratadas como postergadas.
- Enquanto esta diretriz estiver vigente, o backlog ativo deve priorizar apenas backend, API, autenticação, autorização, importação, estoque, auditoria e testes.

## 4.1 Piloto inicial

Objetivo: validar o fluxo principal de requisição, autorização e retirada com usuários reais, usando materiais de consumo cotidiano e mantendo controle em papel em paralelo.

### Piloto — Escopo incluído

- Cadastro mínimo de usuários, setores e papéis necessários ao piloto.
- Importação/carga inicial de materiais do SCPI via CSV.
- Cadastro de materiais, grupos, subgrupos e saldos iniciais.
- Busca e seleção de materiais para requisição.
- Criação de requisição em rascunho.
- Envio de requisição para autorização.
- Fila de autorizações pendentes.
- Autorização total.
- Autorização parcial.
- Recusa da requisição inteira.
- Reserva de estoque na autorização.
- Fila de atendimento do Almoxarifado.
- Atendimento completo.
- Atendimento parcial.
- Baixa de estoque na retirada.
- Liberação de reserva não entregue.
- Notificações internas essenciais.
- Linha do tempo básica da requisição no domínio e nas APIs.

### Piloto — Fora do escopo

- Relatórios completos.
- Devoluções.
- Saídas excepcionais.
- Estornos operacionais complexos.
- Reimportações recorrentes por interface completa.
- Histórico avançado de importações.
- Painel completo de Gestão do Almoxarifado.
- Exportações CSV dos relatórios.
- Rotinas completas de gestão do Almoxarifado.
- Qualquer implementação de frontend, telas operacionais ou responsividade dedicada.

### Piloto — Critério mínimo para entrada em uso real

O piloto só deve iniciar com usuários reais quando estiverem funcionando:

- login por matrícula;
- permissões básicas por papel;
- carga inicial de materiais e saldos;
- criação de requisição válida;
- envio para autorização;
- autorização total/parcial e recusa;
- reserva de estoque;
- atendimento total/parcial;
- baixa de estoque na retirada;
- liberação de reserva não entregue;
- visualização de minhas requisições;
- fila de autorizações;
- fila de atendimento;
- linha do tempo básica;
- notificações essenciais;
- controle em papel paralelo definido.

## 4.1.1 Base mínima de acesso

### PIL-BE-ACE-001 — Criar modelo de usuário customizado

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** Backlog de materialização completo (`MAT-000` a `MAT-006`)
- **Objetivo:** criar o app de usuários do ERP-SAEP em `apps/users/` com usuário customizado por matrícula funcional.
- **Contexto técnico:**
  - A materialização mínima (`docs/backlog/backlog-materializacao-django.md`) cria apenas a base Django e não cria `apps/users/`.
  - Esta tarefa é a primeira do backlog funcional, após a base técnica estar pronta.
  - Esta tarefa deve criar `apps/users/` como app de usuários oficial do ERP-SAEP.
  - Não criar novo app `accounts` ou outro app de usuários sem decisão registrada.
  - Implementar `apps/users/models.py`, `managers.py`, `forms.py`, `admin.py` e configurações relacionadas.
- **Regras de negócio:**
  - O login deve ser feito pela matrícula funcional.
  - A matrícula funcional deve ser única.
  - CPF e telefone não devem ser mantidos como campos cadastrais permanentes do usuário.
  - Usuários devem possuir status ativo/inativo.
  - O projeto deve usar usuário customizado desde o início.
  - Não implementar setores nesta tarefa, exceto se for necessário deixar referência técnica mínima ou TODO para `PIL-BE-ACE-002`.
  - Não implementar papéis completos nesta tarefa; isso pertence à tarefa `PIL-BE-ACE-003`.
- **Entregáveis:**
  - App `apps/users/` criado como app oficial de usuários.
  - Modelo de usuário customizado com matrícula funcional.
  - Validação de matrícula funcional única.
  - Ajustes em manager, forms, admin e autenticação quando necessário.
  - Migração correspondente.
  - Testes automatizados para matrícula única e status ativo/inativo quando aplicável.
- **Testes esperados:**
  - Criar usuário ativo com matrícula única.
  - Impedir matrícula duplicada.
  - Garantir que CPF e telefone não sejam campos cadastrais permanentes.
  - Validar que usuário inativo não deve ser tratado como apto ao acesso.
- **Critérios de aceite relacionados:** 11.1, 11.6

### PIL-BE-ACE-002 — Criar modelo de setor

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-001
- **Objetivo:** criar a estrutura de setores organizacionais do SAEP.
- **Regras de negócio:**
  - Todo setor deve ter chefe responsável.
  - Um setor não pode ficar temporariamente sem chefe.
  - Um chefe de setor só pode ser responsável por um setor.
  - Setores inativos permanecem em históricos, mas não recebem novas requisições.
- **Entregáveis:**
  - Modelo/tabela de setores.
  - Relacionamento com chefe responsável.
  - Status ativo/inativo.
- **Testes esperados:**
  - Criar setor com chefe responsável.
  - Impedir setor sem chefe quando a regra já estiver ativa.
  - Impedir que o mesmo chefe seja responsável por mais de um setor.
- **Critérios de aceite relacionados:** 11.3

### PIL-BE-ACE-003 — Criar papéis e permissões mínimas do piloto

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-001, PIL-BE-ACE-002
- **Objetivo:** implementar papéis mínimos necessários ao piloto.
- **Regras de negócio:**
  - Todo usuário ativo é solicitante por padrão.
  - O piloto deve conter permissões para solicitante, auxiliar de setor, chefe de setor, funcionário do Almoxarifado, chefe de Almoxarifado e superusuário.
  - Auxiliar de setor pode criar requisições em nome de funcionários do próprio setor.
  - Auxiliar de setor não pode atuar em setores diferentes do seu.
- **Entregáveis:**
  - Enum/tabela de papéis.
  - Vínculo entre usuário, setor e papéis.
  - Funções ou policies de autorização por papel.
- **Testes esperados:**
  - Usuário comum tem permissão de solicitante.
  - Auxiliar de setor possui permissão de criar requisição para funcionário do próprio setor.
  - Auxiliar de setor não possui permissão de criar requisição para funcionário de outro setor.
  - Chefe de setor possui permissão de autorizar apenas seu setor.
  - Funcionário do Almoxarifado pode ver fila de atendimento.
  - Superusuário não opera estoque no dia a dia.
- **Critérios de aceite relacionados:** 11.1 a 11.6

### PIL-BE-ACE-004 — Consolidar login por matrícula funcional

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / API
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-001
- **Objetivo:** garantir que a autenticação local use matrícula funcional e senha.

- **Contexto técnico:**
  - Usar o app `apps/users/` criado em `PIL-BE-ACE-001`.
  - Não criar novo app de autenticação.
  - Se a tarefa `PIL-BE-ACE-001` já tiver ajustado completamente o login por matrícula, esta tarefa deve apenas revisar, testar e ajustar autenticação, managers, adapters e integrações necessárias no backend.
- **Regras de negócio:**
  - A matrícula funcional é o identificador de login.
  - Usuário inativo não deve conseguir acessar o sistema.
  - A autenticação é local, por matrícula e senha.
- **Entregáveis:**
  - Fluxo de autenticação ajustado para matrícula funcional.
  - Managers/adapters/forms backend ajustados quando necessário.
  - Validação de usuário ativo.
  - Testes de autenticação por matrícula.
- **Testes esperados:**
  - Login com matrícula funcional e senha válidas.
  - Bloqueio de usuário inativo.
  - Erro para matrícula inexistente ou senha inválida.
- **Critérios de aceite relacionados:** 11.1

### PIL-BE-ACE-005 — Implementar criação em nome de terceiros no piloto

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-003
- **Objetivo:** implementar regras de atuação em nome de terceiros usadas no piloto.
- **Regras de negócio:**
  - Solicitante comum cria apenas para si mesmo.
  - Auxiliar de setor cria em nome de funcionários do próprio setor.
  - Chefe de setor cria em nome de funcionários do próprio setor.
  - Funcionário do Almoxarifado e chefe de Almoxarifado criam em nome de qualquer funcionário.
  - A requisição sempre pertence ao setor do beneficiário.
- **Entregáveis:**
  - Serviço/policy para validar beneficiário permitido.
  - Testes de permissão por papel.
- **Testes esperados:**
  - Solicitante comum impedido de criar para outro usuário.
  - Auxiliar de setor autorizado a criar para funcionário do próprio setor.
  - Auxiliar de setor impedido de criar para funcionário de outro setor.
  - Chefe de setor impedido de criar para funcionário de outro setor.
  - Almoxarifado autorizado a criar para qualquer setor.
- **Critérios de aceite relacionados:** 1.1, 1.2, 11.1 a 11.5

## 4.1.2 Materiais e carga inicial

### PIL-BE-MAT-001 — Criar modelos de grupo e subgrupo de material

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** nenhuma
- **Objetivo:** criar cadastros estruturais de grupo e subgrupo conforme origem SCPI.
- **Regras de negócio:**
  - Grupo e subgrupo vêm do SCPI via importação CSV.
  - Grupo e subgrupo não possuem status ativo/inativo próprio no MVP.
  - Subgrupo deve estar vinculado a um grupo pai.
- **Entregáveis:**
  - Modelo/tabela de grupo de material.
  - Modelo/tabela de subgrupo de material.
  - Relacionamento entre subgrupo e grupo.
- **Testes esperados:**
  - Criar grupo.
  - Criar subgrupo vinculado a grupo.
  - Impedir subgrupo sem grupo pai.
- **Critérios de aceite relacionados:** 7.1, 8.6

### PIL-BE-MAT-002 — Criar modelo de material

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-MAT-001
- **Objetivo:** criar a estrutura persistente dos materiais controlados pelo Almoxarifado.
- **Regras de negócio:**
  - Código completo deve seguir o padrão `xxx.yyy.zzz`.
  - Dados cadastrais provenientes do SCPI não devem ser editados diretamente no ERP-SAEP.
  - Unidade de medida vem do SCPI e não deve ser alterada pelo usuário no MVP.
- **Entregáveis:**
  - Modelo/tabela de material.
  - Campos de código completo, grupo, subgrupo, sequencial, nome, descrição, unidade de medida, status e observações internas.
  - Validação de código completo único.
- **Testes esperados:**
  - Criar material com código válido.
  - Impedir código duplicado.
  - Impedir alteração direta de campos oficiais do SCPI em fluxo operacional comum.
- **Critérios de aceite relacionados:** 7.1, 8.6

### PIL-BE-EST-001 — Criar modelo de estoque por material

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-MAT-002
- **Objetivo:** armazenar saldo físico e saldo reservado por material.
- **Regras de negócio:**
  - O MVP possui apenas um almoxarifado físico.
  - Cada material possui um registro geral de estoque.
  - Saldo disponível deve ser calculado como `saldo físico - saldo reservado`.
  - Saldo disponível não precisa ser armazenado.
- **Entregáveis:**
  - Modelo/tabela de estoque.
  - Campos de saldo físico e saldo reservado.
  - Método/função para calcular saldo disponível.
- **Testes esperados:**
  - Calcular saldo disponível corretamente.
  - Permitir saldo disponível negativo apenas quando houver divergência crítica após importação futura.
- **Critérios de aceite relacionados:** 7.2

### PIL-BE-IMP-001 — Implementar normalização mínima do CSV SCPI para carga inicial

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de importação
- **Depende de:** PIL-BE-MAT-001, PIL-BE-MAT-002, PIL-BE-EST-001
- **Objetivo:** permitir carga inicial técnica dos materiais e saldos vindos do SCPI.
- **Regras de negócio:**
  - CSV usa UTF-8 com BOM e separador `;`.
  - Produto lógico começa quando a linha inicia com código no padrão `000.000.000;`.
  - Linhas sem código inicial são continuação da descrição do produto anterior.
  - A carga inicial pode ser feita por script técnico durante o piloto.
- **Entregáveis:**
  - Parser/normalizador mínimo do CSV.
  - Mapeamento dos campos essenciais: código, grupo, subgrupo, nome, descrição, unidade e `QUAN3`.
  - Relatório simples de carga executada.
- **Testes esperados:**
  - Ler CSV com BOM.
  - Reconstruir descrição quebrada em múltiplas linhas.
  - Criar produtos lógicos com colunas coerentes.
- **Critérios de aceite relacionados:** 8.1, 8.6

### PIL-BE-IMP-002 — Registrar saldo inicial via QUAN3

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-IMP-001
- **Objetivo:** criar saldos iniciais a partir do campo `QUAN3` do SCPI.
- **Regras de negócio:**
  - `QUAN3` define o saldo físico inicial.
  - Toda carga inicial deve gerar movimentação de entrada por saldo inicial.
- **Entregáveis:**
  - Criação/atualização de estoque inicial.
  - Registro de movimentação de entrada por saldo inicial.
- **Testes esperados:**
  - Material novo recebe saldo físico inicial.
  - Movimentação de saldo inicial é registrada.
  - Saldo reservado começa zerado.
- **Critérios de aceite relacionados:** 8.6, 8.9

### PIL-BE-MAT-003 — Implementar busca de materiais para requisição via API/serviço

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / API
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-MAT-002, PIL-BE-EST-001
- **Objetivo:** disponibilizar busca de materiais para criação de requisições sem depender de frontend.
- **Regras de negócio:**
  - Busca deve aceitar código completo, nome, descrição, grupo e subgrupo.
  - Resultado deve retornar código completo, nome, unidade de medida e saldo disponível.
  - Materiais inativos não aparecem para seleção de nova requisição.
- **Entregáveis:**
  - Endpoint/serviço de busca.
  - Retorno de saldo disponível.
  - Testes automatizados da busca.
- **Testes esperados:**
  - Buscar por código.
  - Buscar por nome.
  - Não retornar material inativo para seleção.
- **Critérios de aceite relacionados:** 7.1, 1.1

### PIL-FE-MAT-004 — Implementar componente visual de busca e seleção de materiais

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Frontend
- **Agente sugerido:** Agente frontend
- **Depende de:** PIL-BE-MAT-003
- **Objetivo:** permitir seleção visual de materiais ao criar requisições.
- **Regras de negócio:**
  - Interface deve usar a busca backend de materiais.
  - Interface deve exibir código completo, nome, unidade de medida e saldo disponível.
  - Interface deve impedir ou indicar bloqueios de material inativo e saldo indisponível.
- **Entregáveis:**
  - Componente de busca na interface.
  - Seleção visual de material.
  - Exibição de saldo disponível.
- **Testes esperados:**
  - Buscar e selecionar material pelo fluxo visual.
  - Exibir saldo disponível.
  - Não permitir seleção visual de material bloqueado.
- **Critérios de aceite relacionados:** 7.1, 1.1

## 4.1.3 Requisições

### PIL-BE-REQ-001 — Criar modelos de requisição e item da requisição

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-005, PIL-BE-MAT-002
- **Objetivo:** criar a estrutura persistente do cabeçalho e dos itens de requisição.
- **Regras de negócio:**
  - Toda requisição começa como `rascunho`.
  - O campo de número público deve permitir requisição em rascunho sem número até o primeiro envio para autorização.
  - A requisição deve registrar criador, beneficiário e setor do beneficiário.
  - Uma requisição deve possuir um ou mais itens.
  - Cada item guarda quantidade solicitada, autorizada e entregue separadamente.
- **Entregáveis:**
  - Modelo/tabela de requisição.
  - Modelo/tabela de item da requisição.
  - Campo de número público opcional, com unicidade para valores preenchidos.
  - Enum/status da requisição.
  - Relacionamentos com usuário, setor e material.
- **Testes esperados:**
  - Criar requisição com item válido.
  - Criar requisição em rascunho sem número público.
  - Impedir requisição sem item.
  - Registrar criador, beneficiário e setor correto.
- **Critérios de aceite relacionados:** 1.1, 1.2

### PIL-BE-REQ-002 — Implementar numeração anual da requisição

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-001
- **Objetivo:** gerar número público de requisição no padrão `REQ-AAAA-NNNNNN` no primeiro envio para autorização.
- **Regras de negócio:**
  - Rascunhos nunca enviados para autorização não possuem número público.
  - O número público deve ser gerado apenas no primeiro envio para autorização.
  - A sequência deve reiniciar a cada ano.
  - O número deve ser único.
  - Requisições que retornarem para rascunho após envio devem preservar o mesmo número em reenvios.
- **Entregáveis:**
  - Serviço de geração de número.
  - Proteção contra colisão/concorrência.
  - Campo de número público opcional enquanto a requisição estiver em rascunho nunca enviado.
- **Testes esperados:**
  - Rascunho recém-criado não possui número público.
  - Primeiro envio gera primeiro número do ano.
  - Novo primeiro envio no mesmo ano incrementa a sequência.
  - Primeiro envio em novo ano reinicia a sequência.
  - Reenvio após retorno para rascunho mantém o mesmo número.
- **Critérios de aceite relacionados:** 1.1

### PIL-BE-REQ-003 — Implementar criação de requisição em rascunho

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-001, PIL-BE-MAT-003
- **Objetivo:** permitir criação de requisição válida em rascunho.
- **Regras de negócio:**
  - Não permitir salvar rascunho sem itens.
  - Não permitir material inativo.
  - Não permitir material com saldo disponível igual ou menor que zero.
  - Não permitir quantidade solicitada maior que saldo disponível no momento da criação.
  - A requisição deve ficar vinculada ao setor do beneficiário.
  - Rascunho recém-criado não deve possuir número público.
- **Entregáveis:**
  - Endpoint/serviço de criação.
  - Validações de item e saldo.
  - Persistência do status `rascunho`.
  - Persistência sem número público até o primeiro envio para autorização.
- **Testes esperados:**
  - Criar rascunho válido.
  - Confirmar que rascunho recém-criado não consome número público.
  - Bloquear material sem saldo.
  - Bloquear quantidade acima do saldo disponível.
  - Bloquear material inativo.
- **Critérios de aceite relacionados:** 1.1, 1.3, 1.4

### PIL-BE-REQ-004 — Implementar criação para si mesmo e em nome de terceiros

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de permissões
- **Depende de:** PIL-BE-REQ-003, PIL-BE-ACE-005
- **Objetivo:** aplicar permissões de beneficiário na criação da requisição.
- **Regras de negócio:**
  - Todo usuário ativo pode criar para si mesmo.
  - Auxiliar de setor pode criar para funcionário do próprio setor.
  - Chefe de setor pode criar para funcionário do próprio setor.
  - Funcionário do Almoxarifado e chefe de Almoxarifado podem criar para qualquer funcionário.
  - Setor da requisição é sempre o setor do beneficiário.
- **Entregáveis:**
  - Validação de beneficiário permitido no serviço de criação.
  - Testes por papel.
- **Testes esperados:**
  - Solicitante cria para si.
  - Auxiliar de setor cria para funcionário do próprio setor.
  - Auxiliar de setor é bloqueado ao criar para outro setor.
  - Chefe cria para funcionário do próprio setor.
  - Chefe é bloqueado ao criar para outro setor.
  - Almoxarifado cria para qualquer setor.
- **Critérios de aceite relacionados:** 1.1, 1.2, 11.1 a 11.5

### PIL-BE-REQ-005 — Implementar envio para autorização

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-002, PIL-BE-REQ-003
- **Objetivo:** permitir que requisição em rascunho seja enviada para autorização.
- **Regras de negócio:**
  - Apenas requisição em `rascunho` pode ser enviada.
  - Deve possuir pelo menos um item válido.
  - No primeiro envio, deve gerar número público no padrão `REQ-AAAA-NNNNNN`.
  - Se a requisição já tiver número público por envio anterior, deve preservar o mesmo número.
  - Status deve mudar para `aguardando autorização`.
  - Data/hora de envio deve ser registrada.
  - Após envio, não pode haver edição direta dos itens.
- **Entregáveis:**
  - Ação/endpoint de envio.
  - Geração de número público no primeiro envio.
  - Atualização de status e data de envio.
  - Bloqueio de edição direta após envio.
- **Testes esperados:**
  - Enviar rascunho válido.
  - Gerar número público no primeiro envio.
  - Preservar número público no reenvio após retorno para rascunho.
  - Bloquear envio sem item.
  - Bloquear edição direta quando aguardando autorização.
- **Critérios de aceite relacionados:** 1.6, 1.8

### PIL-FE-REQ-006 — Implementar tela de criação e edição de rascunho

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Frontend
- **Agente sugerido:** Agente frontend
- **Depende de:** PIL-BE-REQ-003, PIL-FE-MAT-004
- **Objetivo:** disponibilizar interface para criar requisições em rascunho.
- **Regras de negócio:**
  - Usuário deve selecionar beneficiário permitido.
  - Usuário deve buscar materiais e informar quantidade solicitada.
  - Interface deve impedir ou indicar bloqueios de saldo, material inativo e quantidade inválida.
- **Entregáveis:**
  - Tela de nova requisição.
  - Componentes de seleção de beneficiário e materiais.
  - Botões de salvar rascunho e enviar para autorização.
- **Testes esperados:**
  - Criar requisição pelo fluxo visual.
  - Exibir erro de quantidade maior que saldo.
  - Não exibir ação de editar quando status não permitir.
- **Critérios de aceite relacionados:** 1.1, 1.3, 1.4, 1.8

### PIL-BE-REQ-007 — Implementar retorno para rascunho

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-005
- **Objetivo:** permitir que criador ou beneficiário retornem uma requisição aguardando autorização para rascunho.
- **Regras de negócio:**
  - Só vale para status `aguardando autorização`.
  - Apenas criador ou beneficiário podem executar.
  - Deve manter o mesmo número público da requisição.
  - Deve remover a requisição da fila de autorização.
- **Entregáveis:**
  - Ação/endpoint de retorno para rascunho.
  - Atualização de status.
  - Registro básico na linha do tempo.
- **Testes esperados:**
  - Criador retorna para rascunho.
  - Beneficiário retorna para rascunho.
  - Outro usuário é bloqueado.
- **Critérios de aceite relacionados:** 1.7, 1.8

### PIL-BE-REQ-008 — Implementar cancelamento em rascunho e aguardando autorização

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-005
- **Objetivo:** permitir descarte de rascunho nunca enviado e cancelamento simples de requisições já formalizadas antes da autorização.
- **Regras de negócio:**
  - Criador ou beneficiário podem descartar/excluir rascunho que nunca foi enviado para autorização.
  - Rascunho nunca enviado não possui número público e não deve consumir sequência ao ser descartado.
  - Criador ou beneficiário podem cancelar logicamente rascunho que já foi enviado alguma vez e retornou para rascunho.
  - Criador ou beneficiário podem cancelar em `aguardando autorização`.
  - Não exige justificativa.
  - Não gera reserva nem movimentação de estoque.
- **Entregáveis:**
  - Ação/endpoint de descarte de rascunho nunca enviado.
  - Ação/endpoint de cancelamento pré-autorização para requisição já numerada.
  - Exclusão física ou descarte definitivo apenas para rascunho nunca enviado.
  - Atualização para status `cancelada` para rascunho já numerado e para requisição aguardando autorização.
  - Remoção da fila de autorização quando aplicável.
- **Testes esperados:**
  - Descartar rascunho nunca enviado sem consumir número público.
  - Cancelar logicamente rascunho já numerado.
  - Cancelar aguardando autorização.
  - Confirmar que não houve movimentação de estoque.
- **Critérios de aceite relacionados:** 1.9, 1.10

### PIL-FS-REQ-009 — Implementar painel “Minhas requisições”

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-REQ-003, PIL-BE-REQ-005, PIL-BE-REQ-007, PIL-BE-REQ-008
- **Objetivo:** permitir que usuários acompanhem suas requisições.
- **Regras de negócio:**
  - Deve listar requisições criadas pelo usuário ou em que ele é beneficiário.
  - Deve exibir ações conforme status e permissão.
  - Solicitante comum não acessa relatórios gerais; acompanha suas requisições por este painel.
- **Entregáveis:**
  - Endpoint de listagem filtrada.
  - Tela “Minhas requisições”.
  - Ações: visualizar, editar rascunho, enviar, retornar para rascunho e cancelar quando permitido.
- **Testes esperados:**
  - Usuário vê requisições criadas por ele.
  - Usuário vê requisições em que é beneficiário.
  - Usuário não vê requisições alheias sem permissão.
- **Critérios de aceite relacionados:** 11.1, 1.6 a 1.10

## 4.1.4 Autorizações

### PIL-BE-AUT-001 — Implementar fila de autorizações pendentes

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-005, PIL-BE-ACE-003
- **Objetivo:** listar requisições aguardando autorização para o chefe responsável.
- **Regras de negócio:**
  - Chefe de setor vê apenas requisições cujo beneficiário pertence ao seu setor.
  - Chefe de Almoxarifado vê requisições do setor de Almoxarifado.
  - A autorização pertence ao chefe do setor do beneficiário.
- **Entregáveis:**
  - Endpoint de fila de autorizações.
  - Filtros por chefe/setor.
  - Dados básicos da requisição na fila.
- **Testes esperados:**
  - Chefe vê requisições do próprio setor.
  - Chefe não vê requisições de outro setor.
  - Chefe de Almoxarifado vê requisições do próprio setor quando for autorizador.
- **Critérios de aceite relacionados:** 2.1, 1.2, 11.3

### PIL-FE-AUT-002 — Implementar tela de análise da autorização

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Frontend
- **Agente sugerido:** Agente frontend
- **Depende de:** PIL-BE-AUT-001
- **Objetivo:** permitir que chefe analise itens, saldos e informe quantidades autorizadas.
- **Regras de negócio:**
  - Exibir material, unidade, quantidade solicitada e saldo disponível atual.
  - Permitir autorização total, autorização parcial e recusa da requisição inteira.
  - Exigir justificativa quando quantidade autorizada for menor que solicitada.
- **Entregáveis:**
  - Tela de detalhes para autorização.
  - Campos de quantidade autorizada por item.
  - Campo de justificativa por item parcial.
  - Campo de motivo de recusa.
- **Testes esperados:**
  - Exibir saldo disponível atual.
  - Exigir justificativa em autorização parcial.
  - Exigir motivo na recusa.
- **Critérios de aceite relacionados:** 2.2 a 2.8

### PIL-BE-AUT-003 — Implementar autorização total e parcial

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de regras de negócio
- **Depende de:** PIL-BE-AUT-001, PIL-BE-EST-001
- **Objetivo:** permitir autorização total ou parcial com reserva automática.
- **Regras de negócio:**
  - Quantidade autorizada nunca pode ser maior que quantidade solicitada.
  - Quantidade autorizada não pode ultrapassar saldo disponível atual.
  - Justificativa é obrigatória quando autorizar menos que solicitado.
  - Item pode ser autorizado com quantidade zero se houver justificativa.
  - Requisição autorizada deve ter ao menos um item com quantidade autorizada maior que zero.
- **Entregáveis:**
  - Serviço/endpoint de autorização.
  - Persistência das quantidades autorizadas e justificativas.
  - Atualização do status para `autorizada`.
  - Reserva automática das quantidades autorizadas.
- **Testes esperados:**
  - Autorizar integralmente.
  - Autorizar parcialmente com justificativa.
  - Bloquear parcial sem justificativa.
  - Permitir item zerado com justificativa.
  - Bloquear todos os itens zerados.
- **Critérios de aceite relacionados:** 2.2, 2.3, 2.4, 2.5, 2.8

### PIL-BE-AUT-004 — Implementar recusa da requisição inteira

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-AUT-001
- **Objetivo:** permitir que chefe recuse a requisição inteira.
- **Regras de negócio:**
  - No MVP, a recusa é sempre da requisição inteira.
  - Motivo da recusa é obrigatório.
  - Não há recusa individual por item no MVP.
  - Status deve mudar para `recusada`.
- **Entregáveis:**
  - Ação/endpoint de recusa.
  - Campo de motivo obrigatório.
  - Atualização de status.
- **Testes esperados:**
  - Recusar com motivo.
  - Bloquear recusa sem motivo.
  - Confirmar que não houve reserva de estoque.
- **Critérios de aceite relacionados:** 2.6

### PIL-BE-AUT-005 — Implementar movimentação de reserva por autorização

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-AUT-003
- **Objetivo:** registrar movimentação de estoque quando uma autorização reservar saldo.
- **Regras de negócio:**
  - Reserva aumenta saldo reservado.
  - Reserva reduz saldo disponível, mas não altera saldo físico.
  - Item autorizado com quantidade zero não gera reserva.
- **Entregáveis:**
  - Tipo de movimentação `reserva por autorização`.
  - Registro com saldo reservado anterior e posterior.
  - Vínculo com requisição e item.
- **Testes esperados:**
  - Reserva aumenta saldo reservado.
  - Saldo físico permanece igual.
  - Item zerado não gera reserva.
- **Critérios de aceite relacionados:** 2.2, 2.4, 3.5, 7.2

### PIL-BE-AUT-006 — Implementar recálculo e lock de saldo na autorização

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend especialista em concorrência
- **Depende de:** PIL-BE-AUT-003, PIL-BE-AUT-005
- **Objetivo:** impedir dupla reserva concorrente do mesmo saldo.
- **Regras de negócio:**
  - Saldo disponível deve ser recalculado no momento da confirmação da autorização.
  - O sistema nunca deve permitir que duas autorizações reservem a mesma quantidade simultaneamente.
  - Se saldo mudar durante análise, a autorização deve respeitar o saldo atual.
- **Entregáveis:**
  - Transação/lock no fluxo de autorização.
  - Revalidação de saldo dentro da transação.
  - Erro amigável quando saldo atual for insuficiente.
- **Testes esperados:**
  - Duas autorizações concorrentes para o mesmo material não podem reservar acima do saldo.
  - Autorização é bloqueada quando saldo muda antes da confirmação.
- **Critérios de aceite relacionados:** 2.7, 2.8, 2.9, 2.10

## 4.1.5 Atendimento pelo Almoxarifado

### PIL-BE-ATE-001 — Implementar fila de atendimento do Almoxarifado

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-AUT-003
- **Objetivo:** listar requisições autorizadas aguardando atendimento.
- **Regras de negócio:**
  - Funcionários do Almoxarifado visualizam requisições com status `autorizada`.
  - Fila deve exibir número, beneficiário, setor, chefe que autorizou, data de autorização, quantidade de itens e status.
- **Entregáveis:**
  - Endpoint de fila de atendimento.
  - Filtro por status `autorizada`.
  - Permissão para perfis do Almoxarifado.
- **Testes esperados:**
  - Funcionário do Almoxarifado vê requisições autorizadas.
  - Solicitante comum não acessa fila de atendimento.
- **Critérios de aceite relacionados:** 3.1, 11.4

### PIL-FE-ATE-002 — Implementar tela de atendimento

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Frontend
- **Agente sugerido:** Agente frontend
- **Depende de:** PIL-BE-ATE-001
- **Objetivo:** permitir registro da retirada pelo Almoxarifado.
- **Regras de negócio:**
  - Exibir quantidade solicitada, autorizada, entregue, saldo físico atual e saldo reservado.
  - Permitir quantidade entregue por item.
  - Exigir justificativa quando entrega for menor que quantidade autorizada.
  - Permitir observação geral opcional.
  - Permitir campo livre opcional para pessoa que retirou fisicamente o material quando diferente do beneficiário.
- **Entregáveis:**
  - Tela de atendimento.
  - Campos de entrega por item.
  - Campos de justificativa parcial.
  - Observação geral e pessoa que retirou.
- **Testes esperados:**
  - Registrar atendimento completo pela interface.
  - Exigir justificativa em atendimento parcial.
  - Permitir informar pessoa que retirou.
- **Critérios de aceite relacionados:** 3.2, 3.3, 3.4, 3.9

### PIL-BE-ATE-003 — Implementar atendimento completo

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-ATE-001, PIL-BE-AUT-005
- **Objetivo:** registrar retirada integral dos itens autorizados.
- **Regras de negócio:**
  - Baixa de estoque ocorre somente na retirada final.
  - Quantidade entregue nunca pode ser maior que quantidade autorizada.
  - Atendimento completo ocorre quando todas as quantidades autorizadas são entregues.
  - A saída por requisição reduz saldo físico e consome a reserva correspondente.
- **Entregáveis:**
  - Ação/endpoint de atendimento completo.
  - Movimentação de saída por requisição.
  - Consumo de reserva.
  - Status `atendida`.
- **Testes esperados:**
  - Entrega integral baixa saldo físico.
  - Reserva é consumida.
  - Status muda para `atendida`.
  - Bloquear entrega maior que autorizada.
- **Critérios de aceite relacionados:** 3.2, 7.2

### PIL-BE-ATE-004 — Implementar atendimento parcial e entrega zero por item

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-ATE-003
- **Objetivo:** permitir entrega menor que a autorizada, com justificativa.
- **Regras de negócio:**
  - Entrega menor que autorizada exige justificativa por item.
  - Entrega zero em item autorizado exige justificativa.
  - Quantidade não entregue deve ter reserva liberada.
  - Atendimento parcial encerra a requisição.
  - Requisição atendida parcialmente deve ter ao menos um item com quantidade entregue maior que zero.
- **Entregáveis:**
  - Fluxo de atendimento parcial.
  - Liberação de reserva da parte não entregue.
  - Status `atendida parcialmente`.
  - Movimentações de saída e liberação de reserva.
- **Testes esperados:**
  - Atendimento parcial com justificativa.
  - Entrega zero em item autorizado com justificativa.
  - Reserva não entregue é liberada.
  - Bloquear finalização se todos os itens forem entregues com zero.
- **Critérios de aceite relacionados:** 3.3, 3.4, 3.5, 3.6

### PIL-BE-ATE-005 — Validar saldo físico no atendimento

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de regras de estoque
- **Depende de:** PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** garantir que o Almoxarifado entregue apenas até o saldo físico disponível.
- **Regras de negócio:**
  - No momento da retirada, validar saldo físico atual.
  - Se saldo físico for menor que autorizado, permitir atendimento parcial com justificativa.
  - Se não houver saldo físico para nenhum item, orientar cancelamento da requisição autorizada com justificativa.
- **Entregáveis:**
  - Validação de saldo físico antes da baixa.
  - Mensagens de erro/orientação.
  - Testes de saldo insuficiente.
- **Testes esperados:**
  - Entregar até saldo físico disponível.
  - Bloquear entrega acima do saldo físico.
  - Bloquear atendimento sem nenhum item entregue.
- **Critérios de aceite relacionados:** 3.7, 3.8

### PIL-BE-ATE-006 — Registrar dados da retirada

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ATE-003
- **Objetivo:** registrar metadados do atendimento.
- **Regras de negócio:**
  - Registrar data/hora automaticamente.
  - Registrar funcionário do Almoxarifado responsável.
  - Permitir observação geral opcional.
  - Permitir pessoa que retirou fisicamente o material em campo livre opcional.
- **Entregáveis:**
  - Campos de atendimento na requisição.
  - Persistência de observação geral e pessoa que retirou.
  - Exibição futura no histórico/linha do tempo.
- **Testes esperados:**
  - Registrar usuário responsável.
  - Registrar data/hora.
  - Salvar observação e pessoa que retirou quando preenchidas.
- **Critérios de aceite relacionados:** 3.9

## 4.1.6 Notificações essenciais

### PIL-BE-NOT-001 — Criar modelo de notificação interna

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-ACE-001
- **Objetivo:** criar estrutura mínima de notificações internas.
- **Regras de negócio:**
  - Notificações podem ser destinadas a usuários específicos ou grupos/perfis operacionais.
  - Devem possuir status lida/não lida.
  - Devem possuir objeto relacionado quando aplicável.
- **Entregáveis:**
  - Modelo/tabela de notificação.
  - Campos de destinatário, tipo, título, mensagem, objeto relacionado, status e data.
- **Testes esperados:**
  - Criar notificação individual.
  - Criar notificação para grupo operacional.
  - Marcar como lida.
- **Critérios de aceite relacionados:** 9.1 a 9.7

### PIL-BE-NOT-002 — Gerar notificações essenciais do fluxo principal

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-NOT-001, PIL-BE-REQ-005, PIL-BE-REQ-008, PIL-BE-AUT-003, PIL-BE-AUT-004, PIL-BE-ATE-003
- **Objetivo:** notificar usuários nos eventos principais do piloto.
- **Regras de negócio:**
  - Envio para autorização notifica chefe do setor do beneficiário.
  - Requisição autorizada notifica criador, beneficiário e funcionários do Almoxarifado.
  - Requisição recusada notifica criador e beneficiário.
  - Requisição cancelada notifica criador e beneficiário.
  - Atendimento total ou parcial notifica criador e beneficiário.
- **Entregáveis:**
  - Geração de notificações nos eventos do fluxo.
  - Testes por evento.
- **Testes esperados:**
  - Notificação para chefe ao enviar.
  - Notificação para Almoxarifado ao autorizar.
  - Notificação para criador/beneficiário ao recusar, cancelar e atender.
- **Critérios de aceite relacionados:** 9.1, 9.2, 9.3, 9.4, 9.5

### PIL-FS-NOT-003 — Implementar contador e leitura de notificações

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-NOT-001
- **Objetivo:** permitir que usuários vejam notificações não lidas.
- **Regras de negócio:**
  - Sistema deve exibir contador de notificações não lidas.
  - Usuário deve conseguir marcar notificação como lida.
- **Entregáveis:**
  - Endpoint de contagem/listagem.
  - Componente de notificações na interface.
  - Ação de marcar como lida.
- **Testes esperados:**
  - Contador exibe quantidade correta.
  - Marcar como lida reduz contador.
- **Critérios de aceite relacionados:** 9.7

## 4.1.7 Rastreabilidade mínima

### PIL-BE-AUD-001 — Criar linha do tempo básica da requisição

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Banco de dados
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-REQ-001
- **Objetivo:** registrar eventos básicos do ciclo de vida da requisição.
- **Regras de negócio:**
  - Linha do tempo deve mostrar data/hora, usuário responsável, ação realizada e justificativa/observação quando houver.
  - Todos os usuários com permissão para visualizar a requisição devem ver a linha do tempo completa.
  - Rascunhos nunca enviados para autorização não precisam gerar linha do tempo operacional formal.
  - A linha do tempo operacional deve começar no primeiro envio para autorização, quando a requisição recebe número público.
- **Entregáveis:**
  - Modelo/tabela de eventos da requisição ou mecanismo equivalente.
  - Registro de criação formal no primeiro envio, retorno para rascunho, recusa, autorização, cancelamento e atendimento.
- **Testes esperados:**
  - Rascunho nunca enviado não exige evento operacional formal.
  - Evento de criação formal/envio registrado ao primeiro envio.
  - Evento registrado ao retornar para rascunho.
  - Evento registrado ao autorizar/recusar.
  - Evento registrado ao atender.
- **Critérios de aceite relacionados:** 1.6, 1.7, 2.2, 2.6, 3.2, 3.3

### PIL-FE-AUD-002 — Exibir linha do tempo básica na requisição

- **Status atual:** postergada fora do escopo ativo de backend/API.
- **Fase:** Piloto inicial
- **Tipo:** Frontend
- **Agente sugerido:** Agente frontend
- **Depende de:** PIL-BE-AUD-001
- **Objetivo:** permitir consulta visual do histórico básico da requisição.
- **Regras de negócio:**
  - Eventos do fluxo operacional não devem ser escondidos de usuários autorizados a visualizar a requisição.
- **Entregáveis:**
  - Componente visual de linha do tempo.
  - Exibição em detalhes da requisição.
- **Testes esperados:**
  - Visualizar eventos em ordem cronológica.
  - Exibir justificativas quando existirem.
- **Critérios de aceite relacionados:** 1.6, 6.3

### PIL-BE-AUD-003 — Registrar movimentações principais de estoque

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-IMP-002, PIL-BE-AUT-005, PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** registrar histórico mínimo das movimentações de estoque do piloto.
- **Regras de negócio:**
  - Registrar saldo inicial.
  - Registrar reserva por autorização.
  - Registrar liberação de reserva.
  - Registrar saída por requisição.
- **Entregáveis:**
  - Modelo/tabela de movimentação de estoque.
  - Tipos de movimentação do piloto.
  - Vínculo com material, requisição e item quando aplicável.
- **Testes esperados:**
  - Saldo inicial gera movimentação.
  - Autorização gera reserva.
  - Atendimento gera saída por requisição.
  - Atendimento parcial gera liberação de reserva.
- **Critérios de aceite relacionados:** 7.2, 3.2, 3.3

## 4.1.8 Implantação do piloto

### PIL-DOC-IMP-001 — Definir lista inicial de materiais do piloto

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Implantação / Documentação
- **Agente sugerido:** Agente de implantação
- **Depende de:** PIL-BE-IMP-001
- **Objetivo:** delimitar materiais de consumo cotidiano que entrarão no piloto.
- **Regras de negócio:**
  - Piloto deve focar em limpeza, copa/cozinha, escritório, higiene, café, chá, açúcar, papel higiênico e itens similares.
  - Materiais hidráulicos, elétricos, ferramentas, EPIs e materiais de obra ficam fora do piloto salvo necessidade específica.
- **Entregáveis:**
  - Lista documentada de materiais incluídos.
  - Lista de categorias excluídas.
- **Testes esperados:**
  - Conferência manual com chefe de almoxarifado.
- **Critérios de aceite relacionados:** critérios de sucesso do MVP em `docs/design-acesso-ocasional/mvp-plano-implantacao.md`

### PIL-DOC-IMP-002 — Preparar operação paralela em papel

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Implantação
- **Agente sugerido:** Agente de implantação
- **Depende de:** conclusão do fluxo principal do piloto
- **Objetivo:** garantir validação segura com controle em papel paralelo.
- **Regras de negócio:**
  - Controle em papel deve continuar durante o período de validação.
  - Problemas encontrados devem ser registrados para ajuste.
- **Entregáveis:**
  - Plano de uso paralelo.
  - Registro de problemas encontrados.
  - Critério de comparação entre sistema e papel.
- **Testes esperados:**
  - Conferência de saídas registradas no sistema versus controle paralelo.
- **Critérios de aceite relacionados:** critérios de sucesso do MVP em `docs/design-acesso-ocasional/mvp-plano-implantacao.md`

### PIL-DOC-IMP-003 — Treinar usuários do piloto

- **Status atual:** não iniciada.
- **Fase:** Piloto inicial
- **Tipo:** Implantação / Documentação
- **Agente sugerido:** Agente de implantação
- **Depende de:** conclusão do fluxo principal do piloto
- **Objetivo:** preparar solicitantes, chefes e Almoxarifado para uso real.
- **Regras de negócio:**
  - Solicitantes devem saber criar e acompanhar requisições.
  - Chefes devem saber autorizar e recusar.
  - Almoxarifado deve saber registrar retirada e atendimento parcial.
- **Entregáveis:**
  - Roteiro de treinamento.
  - Guia rápido por perfil.
- **Testes esperados:**
  - Usuário piloto executa fluxo básico assistido.
- **Critérios de aceite relacionados:** critérios de sucesso do MVP em `docs/design-acesso-ocasional/mvp-plano-implantacao.md`

## 5. Ordem sugerida de implementação para agentes

### Fase 1 — Fundação do piloto

1. PIL-BE-ACE-001 — Criar modelo de usuário.
2. PIL-BE-ACE-002 — Criar modelo de setor.
3. PIL-BE-ACE-003 — Criar papéis e permissões mínimas do piloto.
4. PIL-BE-ACE-004 — Implementar login por matrícula funcional.
5. PIL-BE-ACE-005 — Implementar criação em nome de terceiros no piloto.
6. PIL-BE-MAT-001 — Criar modelos de grupo e subgrupo de material.
7. PIL-BE-MAT-002 — Criar modelo de material.
8. PIL-BE-EST-001 — Criar modelo de estoque por material.
9. PIL-BE-IMP-001 — Implementar normalização mínima do CSV SCPI para carga inicial.
10. PIL-BE-IMP-002 — Registrar saldo inicial via QUAN3.
11. PIL-BE-MAT-003 — Implementar busca de materiais para requisição via API/serviço.

### Fase 2 — Fluxo principal do piloto

1. PIL-BE-REQ-001 — Criar modelos de requisição e item da requisição.
2. PIL-BE-REQ-002 — Implementar numeração anual da requisição.
3. PIL-BE-REQ-003 — Implementar criação de requisição em rascunho.
4. PIL-BE-REQ-004 — Implementar criação para si mesmo e em nome de terceiros.
5. PIL-BE-REQ-005 — Implementar envio para autorização.
6. PIL-BE-REQ-007 — Implementar retorno para rascunho.
7. PIL-BE-REQ-008 — Implementar cancelamento em rascunho e aguardando autorização.
8. PIL-BE-AUT-001 — Implementar fila de autorizações pendentes.
9. PIL-BE-AUT-003 — Implementar autorização total e parcial.
10. PIL-BE-AUT-004 — Implementar recusa da requisição inteira.
11. PIL-BE-AUT-005 — Implementar movimentação de reserva por autorização.
12. PIL-BE-AUT-006 — Implementar recálculo e lock de saldo na autorização.
13. PIL-BE-ATE-001 — Implementar fila de atendimento do Almoxarifado.
14. PIL-BE-ATE-003 — Implementar atendimento completo.
15. PIL-BE-ATE-004 — Implementar atendimento parcial e entrega zero por item.
16. PIL-BE-ATE-005 — Validar saldo físico no atendimento.
17. PIL-BE-ATE-006 — Registrar dados da retirada.

### Fase 3 — Notificações, rastreabilidade e validação do piloto

1. PIL-BE-NOT-001 — Criar modelo de notificação interna.
2. PIL-BE-NOT-002 — Gerar notificações essenciais do fluxo principal.
3. PIL-BE-AUD-001 — Criar linha do tempo básica da requisição.
4. PIL-BE-AUD-003 — Registrar movimentações principais de estoque.
5. PIL-DOC-IMP-001 — Definir lista inicial de materiais do piloto.
6. PIL-DOC-IMP-002 — Preparar operação paralela em papel.
7. PIL-DOC-IMP-003 — Treinar usuários do piloto.

### Tarefas postergadas de frontend/fullstack

Estas tarefas não fazem parte da ordem ativa de implementação enquanto o escopo atual permanecer backend/API:

1. PIL-FE-MAT-004 — Implementar componente visual de busca e seleção de materiais.
2. PIL-FE-REQ-006 — Implementar tela de criação e edição de rascunho.
3. PIL-FS-REQ-009 — Implementar painel “Minhas requisições”.
4. PIL-FE-AUT-002 — Implementar tela de análise da autorização.
5. PIL-FE-ATE-002 — Implementar tela de atendimento.
6. PIL-FS-NOT-003 — Implementar contador e leitura de notificações.
7. PIL-FE-AUD-002 — Exibir linha do tempo básica na requisição.
