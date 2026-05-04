# Arquitetura do Frontend — Piloto

## 1. Objetivo

Definir a arquitetura operacional do frontend do piloto do WMS-SAEP, alinhada ao backend Django já existente e ao fluxo real de criação, autorização e atendimento de requisições.

Este documento é canônico para:

- stack do frontend;
- estrutura de pastas;
- fronteiras entre backend e SPA;
- bloco 0 de APIs habilitadoras;
- sequência de implementação;
- integração com `Makefile`, OpenAPI, seed mínima e CI.

## 2. Escopo ativo

O frontend do piloto faz parte do escopo ativo do projeto.

O objetivo não é abrir uma frente genérica de UI, e sim entregar a interface operacional mínima do piloto para:

- solicitante;
- auxiliar de setor;
- chefe de setor;
- auxiliar de Almoxarifado;
- chefe de Almoxarifado.

O `superusuário` permanece fora do foco da SPA no primeiro corte, usando admin e superfícies técnicas já existentes.

## 3. Princípios

- SPA separada em `frontend/`, no mesmo repositório.
- Backend Django continua dono do domínio, autenticação, autorização e OpenAPI.
- Frontend só avança de verdade após o bloco 0 de APIs habilitadoras.
- UX orientada a worklists, não CRUD genérico.
- Linguagem canônica do domínio preservada na UI, com microcopy pedagógica quando necessário.
- Abstração mínima: abstrair só depois do segundo uso real.
- Validação local no frontend serve à UX; domínio e concorrência continuam no backend.
- Tema claro único, PT-BR, desktop-first com responsividade funcional.

## 4. Stack

- `React`
- `TypeScript`
- `Vite`
- `TanStack Query`
- `TanStack Router`
- `TanStack Table`
- `React Hook Form`
- `Zod`
- `openapi-typescript`
- `openapi-fetch`
- `Tailwind CSS`
- `shadcn/ui`
- `Radix UI`
- `Playwright`
- `pnpm`

## 5. Estrutura de pastas

```text
frontend/
  openapi/
    schema.json
  tests/
    e2e/
  package.json
  tsr.config.json
  tsconfig.json
  vite.config.ts
  vitest.config.ts
  playwright.config.ts
  src/
    app/
      layouts/
      providers/
      router.tsx
    routes/
    routeTree.gen.ts
    shared/
      api/
        schema.d.ts
      auth/
      config/
      lib/
      ui/
    features/
      auth/
      materials/
      requisitions/
      approvals/
      fulfillment/
    tests/
```

Regras:

- `routes/` orquestra páginas, search params, loaders e guards.
- `features/` concentra blocos de domínio e fluxos.
- `shared/` contém apenas primitives transversais.
- `routeTree.gen.ts` e `shared/api/schema.d.ts` são artefatos gerados; não editar manualmente.
- qualquer artefato que “conhece” requisição, autorização ou atendimento pertence a feature, não a `shared`.

## 6. Auth e sessão

- autenticação por sessão Django com CSRF;
- frontend opera com um único `papel` operacional principal por usuário no piloto atual;
- `GET /api/v1/auth/me/` é a base para home, menu e guards;
- capacidades no frontend são derivadas do `papel`;
- sessão expirada deve gerar fluxo estrito: aviso + redirecionamento para login.

Superfície esperada:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`

## 7. Rotas e jornadas

Rotas públicas da SPA:

- `/login`
- `/minhas-requisicoes`
- `/requisicoes/nova`
- `/requisicoes/:id`
- `/autorizacoes`
- `/atendimentos`

Regras:

- `/requisicoes/:id` é a rota canônica de detalhe;
- worklists entram no detalhe com `?contexto=autorizacao` ou `?contexto=atendimento`;
- sem `contexto`, o detalhe fica em modo neutro;
- worklists especializadas continuam com endpoints próprios de backend.

Homes por papel:

- `solicitante`: `Minhas requisições`
- `auxiliar_setor`: `Minhas requisições`
- `chefe_setor`: `Fila de autorizações`
- `auxiliar_almoxarifado`: `Fila de atendimento`
- `chefe_almoxarifado`: `Fila de atendimento`

## 8. Bloco 0 de APIs habilitadoras

O frontend do piloto fica bloqueado até concluir:

1. Auth/sessão:
   - `GET /api/v1/auth/csrf/`
   - `POST /api/v1/auth/login/`
   - `POST /api/v1/auth/logout/`
   - `GET /api/v1/auth/me/`
2. Lookup de beneficiário:
   - `GET /api/v1/users/beneficiary-lookup/?q=...`
3. Leituras canônicas de requisição:
   - `GET /api/v1/requisitions/`
   - `GET /api/v1/requisitions/{id}/`
4. Update de rascunho:
   - ação/endpoint explícito de atualização por substituição completa do rascunho

Regras complementares:

- lookup de beneficiário busca por nome;
- mínimo de 3 caracteres;
- retorno curto, sem paginação;
- só usuários ativos e aptos ao fluxo;
- `GET /api/v1/requisitions/` deve ser paginado e ter busca textual simples + filtro por status;
- lista de requisições usa serializer próprio e mais leve que o detalhe.

## 9. Sequência de implementação

1. Bloco 0 de backend
2. Fundação do frontend:
   - `frontend/`
   - Vite
   - providers
   - router
   - client OpenAPI
   - layout base
   - integração com `Makefile`
3. Login e sessão atual
4. `Minhas requisições`
5. `Nova requisição` + salvar rascunho + editar rascunho + enviar para autorização
6. `Fila de autorizações` + autorização total/parcial + recusa
7. `Fila de atendimento` + atendimento total/parcial + cancelamento operacional permitido
8. Notificações como segunda onda

## 10. Worklists e detalhe

### Minhas requisições

- lista única;
- mostrar `numero_publico` ou badge `Rascunho`;
- destacar beneficiário quando for diferente do usuário logado;
- ordenar por atualização mais recente;
- filtros mínimos: busca textual e status;
- datas exibidas são derivadas contextualmente do status.

### Fila de autorizações

- worklist especializada;
- ordenação por mais antigas pendentes primeiro;
- detalhe abre em `/requisicoes/:id?contexto=autorizacao`;
- ação rápida: `Autorizar tudo como solicitado`.

### Fila de atendimento

- worklist especializada;
- ordenação por mais antigas autorizadas primeiro;
- detalhe abre em `/requisicoes/:id?contexto=atendimento`;
- ação rápida: `Preencher entrega completa`.

### Detalhe canônico

- cabeçalho comum;
- corpo comum com itens, status e resumo de eventos;
- bloco de ações muda conforme `contexto`;
- quando a requisição estiver em `rascunho`, pode reutilizar os mesmos blocos centrais da montagem/edição de rascunho.

## 11. Formulários e tabelas

- criação e edição de rascunho usam a mesma tela;
- atualização de rascunho é por substituição completa;
- formulários de ação são action-oriented:
  - criar requisição
  - enviar para autorização
  - autorizar
  - recusar
  - atender
  - cancelar requisição autorizada
- tabelas usam `TanStack Table`;
- itens mostram `quantidade_solicitada`, `quantidade_autorizada` e `quantidade_entregue` com apresentação contextual;
- divergências entre quantidades devem ser destacadas visualmente;
- justificativas parciais aparecem inline de forma compacta.

## 12. Makefile e operações

O `frontend/` usa `pnpm`, mas o ponto de entrada operacional do repo deve passar pelo `Makefile`.

Rotinas previstas:

- `make frontend-init`
- `make frontend-dev`
- `make frontend-build`
- `make frontend-lint`
- `make frontend-test`
- `make frontend-e2e`
- `make frontend-gen-api`
- `make seed-pilot-minimo`

Significado operacional:

- `make frontend-init`: instala dependências `pnpm` da SPA e prepara Chromium do Playwright;
- `make frontend-gen-api`: exporta `frontend/openapi/schema.json` com `drf-spectacular` e regenera `src/shared/api/schema.d.ts`;
- `make frontend-dev`: sobe a SPA local em `127.0.0.1:4173`;
- `make frontend-build`: executa `frontend-gen-api` e gera o build;
- `make frontend-lint`: executa `frontend-gen-api`, lint e typecheck;
- `make frontend-test`: executa `frontend-gen-api` e smoke tests com Vitest;
- `make frontend-e2e`: executa `frontend-gen-api` e smoke E2E com Playwright.

## 13. OpenAPI

- o backend exporta o schema para arquivo;
- o frontend consome `frontend/openapi/schema.json`;
- os tipos TS gerados vivem em `frontend/src/shared/api/schema.d.ts`;
- geração de tipos não deve depender do endpoint HTTP `/api/v1/schema/` em runtime de build;
- arquivos gerados não devem ser editados manualmente.

## 14. Seed mínima

Deve existir um comando oficial de backend para popular o cenário mínimo do piloto:

- nome proposto: `seed_pilot_minimo`
- exposto por `make seed-pilot-minimo`

Conteúdo mínimo:

- usuários operacionais principais
- 1 usuário inativo apenas para autenticação
- setores coerentes
- materiais:
  - ativo com saldo confortável
  - ativo com saldo baixo
  - ativo sem estoque associado
  - inativo
- requisições de exemplo:
  - rascunho
  - aguardando autorização
  - autorizada com caso de autorização parcial
  - atendida parcialmente
  - ao menos uma criada para terceiro

Essa seed é base oficial tanto para validação manual quanto para Playwright local.

Fluxo operacional esperado no ambiente efêmero:

- rodar `rtk make setup`
- rodar `rtk make seed-pilot-minimo`
- usar esse mesmo cenário como baseline para validação manual local e para E2E com Playwright

## 15. CI

Entrada em duas fases:

### Fase 1

- instalar dependências do frontend
- gerar tipos OpenAPI
- lint
- build

### Fase 2

- subir backend com bloco 0 estável
- carregar `seed_pilot_minimo`
- rodar Playwright
