# ADR 0001 — Frontend do piloto como SPA separada

## Status

Aceita.

## Contexto

O WMS-SAEP nasceu com foco backend/API-first e com frontend fora do escopo ativo. A base backend do piloto já cobre o fluxo central de requisição, autorização e atendimento, mas o piloto operacional precisa agora de uma interface web dedicada para solicitantes, chefes de setor e Almoxarifado.

Ao mesmo tempo, o repositório já possui contratos HTTP explícitos, autenticação por sessão Django com CSRF, OpenAPI via drf-spectacular e forte separação entre regras de domínio e superfícies de API. A arquitetura do frontend precisa preservar essas decisões e evitar um acoplamento confuso com templates server-rendered ou superfícies administrativas do Django.

## Decisão

O frontend do piloto passa a fazer parte do escopo ativo do projeto, com as seguintes decisões macro:

- o frontend será uma SPA separada em `frontend/`, no mesmo repositório;
- o backend Django continua como fonte de verdade para domínio, autenticação, autorização, OpenAPI e regras transacionais;
- a autenticação da SPA usará sessão Django com CSRF;
- a stack inicial do frontend será:
  - `React + TypeScript + Vite`
  - `TanStack Query`
  - `TanStack Router`
  - `TanStack Table`
  - `React Hook Form + Zod`
  - `openapi-typescript` + `openapi-fetch`
  - `Tailwind CSS + shadcn/ui + Radix UI`
  - `Playwright`
- a organização interna do frontend será feature-based, com `shared/` mínimo e controlado;
- o frontend do piloto será desktop-first, PT-BR, tema claro único e UX operacional guiada por worklists;
- o fluxo principal da SPA será:
  - `Minhas requisições`
  - `Nova requisição` / edição de rascunho
  - `Fila de autorizações`
  - `Fila de atendimento`
- notificações ficam fora do primeiro corte e entram como segunda onda;
- o frontend fica bloqueado até a conclusão do bloco 0 de APIs habilitadoras do backend.

## Bloco 0 obrigatório

Antes de implementar as features operacionais da SPA, o backend deve expor:

1. Autenticação e sessão para SPA:
   - `GET /api/v1/auth/csrf/`
   - `POST /api/v1/auth/login/`
   - `POST /api/v1/auth/logout/`
   - `GET /api/v1/auth/me/`
2. Lookup de beneficiário por nome:
   - `GET /api/v1/users/beneficiary-lookup/?q=...`
3. Leituras canônicas de requisição:
   - `GET /api/v1/requisitions/`
   - `GET /api/v1/requisitions/{id}/`
4. Atualização explícita de rascunho por substituição completa:
   - ação/endpoint próprio para atualizar rascunho existente

## Consequências

### Positivas

- preserva a arquitetura backend/API-first já consolidada;
- dá uma superfície web própria ao piloto sem contaminar o Django com UI acoplada;
- mantém o OpenAPI como contrato vivo entre backend e frontend;
- favorece UX operacional clara para perfis de baixa familiaridade tecnológica;
- permite integrar frontend, seed mínima e Playwright de forma reproduzível via `Makefile`.

### Negativas / Custos

- introduz toolchain Node adicional no repositório;
- exige bloco 0 de APIs habilitadoras antes do avanço real da SPA;
- adiciona nova frente de CI, build e documentação;
- requer seed oficial mínima para suportar desenvolvimento manual e E2E.

## Alternativas consideradas

### Manter frontend fora do escopo ativo

Rejeitada porque o piloto precisa de interface operacional para fechar o fluxo real com usuários.

### Usar templates server-rendered no Django

Rejeitada porque reduziria a separação entre domínio/API e UI, e não aproveitaria bem o OpenAPI já existente.

### Criar frontend com autenticação baseada em JWT

Rejeitada porque o projeto já padronizou autenticação por sessão Django com CSRF, e não há necessidade atual de consumidor externo/mobile.

### Criar múltiplos ADRs pequenos desde já

Rejeitada porque a primeira decisão de frontend ainda é macro e coerente o suficiente para um único ADR inicial.
