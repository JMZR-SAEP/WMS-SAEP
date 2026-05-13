# QA de lançamento do frontend do piloto

Fonte rápida para validar a issue #70. Este checklist não substitui os testes automatizados; ele registra o gate final antes de liberar o piloto.

## Regras do gate

- Status permitido por critério: `Aprovado` ou `Bloqueado`.
- Se qualquer critério P0 ficar `Bloqueado`, o lançamento fica bloqueado.
- Playwright mobile é validação complementar por emulação. Chrome Android atual e Safari iOS atual exigem QA manual em dispositivo real.
- Não registrar nomes de usuários, materiais, números de requisição, prints com dados pessoais ou qualquer PII nas evidências.
- Bugs de produto encontrados aqui devem bloquear o critério e virar issue/PR próprio, salvo ajuste pequeno de teste ou checklist.

## Checks automatizados obrigatórios

| Critério | Ambiente | Comando | Evidência | Status | Observação |
| --- | --- | --- | --- | --- | --- |
| Smoke/unit frontend | Local/CI | `rtk make frontend-test` | Saída do comando | Aprovado/Bloqueado | Deve cobrir router, PWA, SLA, analytics sem PII. |
| Lint/typecheck frontend | Local/CI | `rtk make frontend-lint` | Saída do comando | Aprovado/Bloqueado | Regenera OpenAPI/types antes de validar. |
| Build frontend | Local/CI | `rtk make frontend-build` | Saída do comando | Aprovado/Bloqueado | Não deve gerar diff inesperado em artefatos. |
| E2E real | Local/CI | `rtk make frontend-e2e` | Relatório Playwright | Aprovado/Bloqueado | Roda desktop Chromium e smokes `@qa-final` em mobile Chrome/WebKit. |

## Matriz manual P0

| Critério | Ambiente | Passos | Evidência | Status | Observação |
| --- | --- | --- | --- | --- | --- |
| Login mobile sem overflow horizontal | Chrome Android atual | Abrir login, focar matrícula, entrar como solicitante. | Resultado textual, sem print com PII. | Aprovado/Bloqueado | Deve preservar foco visível e logo SAEP. |
| Nova requisição mobile | Chrome Android atual | Criar rascunho para terceiro, adicionar item, revisar. | Resultado textual. | Aprovado/Bloqueado | Teclado decimal PT-BR e CTA fixa não podem cobrir campo. |
| Queda de conexão preserva rascunho | Chrome Android atual | Preencher rascunho, simular offline/falha, recarregar. | Resultado textual. | Aprovado/Bloqueado | Dados locais devem reaparecer sem operação offline completa. |
| Fila de autorizações mobile | Chrome Android atual | Entrar como chefe, abrir fila e detalhe. | Resultado textual. | Aprovado/Bloqueado | Sem scroll horizontal; SLA não depende só de cor. |
| Push negado não bloqueia fila | Chrome Android atual | Negar permissão de push e voltar para autorizações. | Resultado textual. | Aprovado/Bloqueado | Aviso persistente deve explicar próximo passo. |
| PWA/push state no iOS | Safari iOS atual com PWA instalado | Abrir app instalado, acessar Alertas. | Resultado textual. | Aprovado/Bloqueado | Safari no navegador não substitui PWA instalado. |
| Deep link de push | Safari iOS atual com PWA instalado | Abrir link de detalhe com `?contexto=autorizacao`. | Resultado textual. | Aprovado/Bloqueado | Deve abrir detalhe canônico em contexto de autorização. |
| Desktop Almoxarifado | Desktop Chrome atual | Entrar como Almoxarifado e abrir fila/detalhe de atendimento. | Resultado textual. | Aprovado/Bloqueado | Layout denso deve seguir útil em desktop/tablet. |

## Acessibilidade P0

| Critério | Ambiente | Como validar | Evidência | Status | Observação |
| --- | --- | --- | --- | --- | --- |
| Foco visível | Mobile/desktop | Navegar por teclado nas telas P0. | Resultado textual. | Aprovado/Bloqueado | Foco deve estar visível em links, botões e inputs. |
| Labels e hints | Mobile/desktop | Verificar inputs de login, beneficiário, material e quantidade. | Resultado textual. | Aprovado/Bloqueado | Não aceitar label apenas por placeholder. |
| Ordem de foco | Mobile/desktop | Tab/shift-tab nos fluxos P0. | Resultado textual. | Aprovado/Bloqueado | Ordem deve seguir leitura visual. |
| Dialogs | Mobile/desktop | Abrir confirmação de envio/recusa/parcial. | Resultado textual. | Aprovado/Bloqueado | Deve ter `aria-modal`, título e retorno de foco. |
| Erros | Mobile/desktop | Forçar erro de API ou validação. | Resultado textual. | Aprovado/Bloqueado | Mensagem humana e detalhes copiáveis quando houver trace/código. |
| Cor não exclusiva | Mobile/desktop | Checar status, SLA, erro e sucesso. | Resultado textual. | Aprovado/Bloqueado | Texto/ícone deve complementar cor. |
| Alvos de toque | Mobile | Inspecionar botões/links P0. | Resultado textual. | Aprovado/Bloqueado | Área interativa mínima 44px. |
| Overflow horizontal | Mobile | Inspecionar `scrollWidth <= clientWidth`. | Resultado textual. | Aprovado/Bloqueado | Zero scroll horizontal nos fluxos P0. |

## Limitação registrada

`mobile-safari-webkit` no Playwright valida WebKit com perfil de iPhone, mas não prova Safari iOS real, permissão PWA real ou comportamento de push em dispositivo. O gate só fica completo com QA manual em Safari iOS atual com PWA instalado.
