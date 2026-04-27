# Backlog Técnico — MVP Completo

Este documento reúne apenas o escopo do MVP completo e do pós-MVP.

Para o backlog do piloto inicial, consultar `docs/backlog/backlog-tecnico-piloto.md`.

A numeração das seções foi preservada em relação ao backlog original para manter referências estáveis entre documentos.

## 4.2 MVP completo

Observação de escopo atual:

- Tarefas identificadas como `FE` ou `fullstack`, bem como entregáveis descritos como telas, painéis ou componentes visuais, permanecem como planejamento futuro e não entram no escopo ativo agora.
- O backlog executável neste momento deve priorizar backend, API, importação, permissões, estoque, auditoria, relatórios exportáveis e testes.

Objetivo: completar a primeira versão operacional mínima após validação do piloto, adicionando rotinas complementares, relatórios, gestão e rastreabilidade mais completa.

### MVP completo — Escopo incluído

- Importação CSV com pré-visualização técnica.
- Histórico completo de importações CSV.
- Tratamento completo de materiais ausentes no CSV.
- Tratamento completo de divergências críticas.
- Devoluções vinculadas a requisição.
- Saídas excepcionais.
- Estornos operacionais.
- Cancelamentos em todos os estados permitidos.
- Correção e reenvio de requisição recusada.
- Cópia de requisição atendida ou atendida parcialmente.
- Relatórios iniciais do MVP.
- Exportação CSV dos relatórios principais.
- Auditoria e histórico operacional completos.
- Regras completas de expiração/resolução de notificações.
- Eventual frontend operacional, se aprovado em decisão técnica posterior.

## 4.2.1 Épico 1 — Base do sistema e permissões

### MVP-BE-ACE-001 — Completar permissões de todos os papéis

- **Fase:** MVP completo
- **Tipo:** Backend / Testes
- **Agente sugerido:** Agente backend de permissões
- **Depende de:** PIL-BE-ACE-003
- **Objetivo:** consolidar permissões completas dos papéis do MVP.
- **Regras de negócio:**
  - Solicitante comum cria apenas para si e visualiza suas requisições.
  - Auxiliar de setor cria em nome de funcionários do próprio setor.
  - Chefe de setor autoriza ou recusa requisições do próprio setor.
  - Funcionário do Almoxarifado registra atendimento e devolução.
  - Chefe de Almoxarifado registra saídas excepcionais e estornos.
  - Superusuário administra cadastros e importação, mas não opera estoque no dia a dia.
- **Entregáveis:**
  - Policies/middlewares completos por papel.
  - Matriz de permissões implementada.
  - Testes automatizados por papel.
- **Testes esperados:**
  - Cobrir critérios 11.1 a 11.6.
- **Critérios de aceite relacionados:** 11.1 a 11.6

### MVP-BE-ACE-002 — Implementar administração técnica de usuários, setores e perfis pelo superusuário

- **Fase:** MVP completo
- **Tipo:** Backend / API
- **Agente sugerido:** Agente backend de administração
- **Depende de:** MVP-BE-ACE-001
- **Objetivo:** permitir gestão administrativa dos cadastros estruturais sem depender de frontend dedicado.
- **Regras de negócio:**
  - Superusuário gerencia usuários, setores, chefes, auxiliares e perfis.
  - Setor não pode ficar sem chefe.
  - Chefe só pode ser responsável por um setor.
- **Entregáveis:**
- Endpoints ou rotinas administrativas autenticadas.
  - Validações estruturais.
  - Auditoria de alterações.
- **Testes esperados:**
  - Criar/editar/inativar usuário.
  - Criar/editar/inativar setor.
  - Impedir setor sem chefe.
  - Impedir chefe em dois setores.
- **Critérios de aceite relacionados:** 11.3, 11.6

## 4.2.2 Épico 2 — Materiais, estoque e importação SCPI CSV

### MVP-BE-IMP-001 — Implementar importação CSV com pré-visualização técnica

- **Fase:** MVP completo
- **Tipo:** Backend / API
- **Agente sugerido:** Agente backend de importação
- **Depende de:** PIL-BE-IMP-001, PIL-BE-IMP-002
- **Objetivo:** permitir importação CSV completa pelo superusuário por fluxo técnico autenticado.
- **Regras de negócio:**
  - Sistema deve normalizar e validar tecnicamente antes de aplicar.
  - Pré-visualização deve mostrar totais, materiais novos, atualizados, saldos atualizados, ausentes, divergências críticas e erros técnicos.
  - Deve permitir cancelar antes da aplicação.
- **Entregáveis:**
- Endpoint ou comando de pré-visualização.
  - Endpoint de validação sem persistência.
  - Resumo categorizado da importação.
- **Testes esperados:**
  - Pré-visualizar CSV válido.
  - Exibir erros técnicos.
  - Cancelar sem persistir alterações.
- **Critérios de aceite relacionados:** 8.1, 8.2

### MVP-BE-IMP-002 — Implementar aplicação transacional e regra tudo ou nada

- **Fase:** MVP completo
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de banco de dados
- **Depende de:** MVP-BE-IMP-001
- **Objetivo:** aplicar importação de forma segura e atômica.
- **Regras de negócio:**
  - Se houver erro técnico impeditivo, nenhuma alteração deve ser persistida.
  - Alertas e divergências não impedem aplicação quando a validação técnica for bem-sucedida.
  - Quando houver alertas, exigir confirmação explícita.
- **Entregáveis:**
  - Aplicação em transação única.
  - Confirmação explícita para alertas.
  - Status `concluída`, `concluída com alertas` ou `falhou`.
- **Testes esperados:**
  - Falha técnica não persiste nada.
  - Alertas permitem aplicação com confirmação.
  - Importação válida persiste materiais e saldos.
- **Critérios de aceite relacionados:** 8.3, 8.4, 8.9

### MVP-BE-IMP-003 — Implementar atualização de saldo físico via QUAN3 em reimportações

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** MVP-BE-IMP-002
- **Objetivo:** atualizar saldo físico de materiais existentes com base no SCPI.
- **Regras de negócio:**
  - `QUAN3` atualiza saldo físico.
  - Atualização via SCPI não é ajuste manual.
  - Deve registrar saldo anterior, saldo novo, diferença, data/hora e usuário responsável.
- **Entregáveis:**
  - Movimentação de atualização de saldo via SCPI.
  - Atualização de estoque existente.
- **Testes esperados:**
  - Atualizar saldo físico existente.
  - Registrar diferença.
  - Não alterar saldo reservado diretamente.
- **Critérios de aceite relacionados:** 8.5

### MVP-BE-IMP-004 — Implementar materiais ausentes no CSV

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Backend / Frontend
- **Agente sugerido:** Agente fullstack
- **Depende de:** MVP-BE-IMP-001
- **Objetivo:** listar materiais existentes no ERP-SAEP que não vieram no CSV.
- **Regras de negócio:**
  - Material ausente no CSV não deve ser inativado automaticamente.
  - Ausência deve aparecer para análise.
  - Lista pode ser exportada.
- **Entregáveis:**
  - Detecção de ausentes.
  - Exibição na pré-visualização e no resultado.
  - Exportação simples se prevista no fluxo.
- **Testes esperados:**
  - Detectar material ausente.
  - Não inativar automaticamente.
- **Critérios de aceite relacionados:** 8.7

### MVP-BE-EST-001 — Implementar divergência crítica de material

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** MVP-BE-IMP-003
- **Objetivo:** bloquear materiais quando saldo físico ficar menor que saldo reservado.
- **Regras de negócio:**
  - Divergência crítica ocorre quando saldo físico importado fica menor que saldo reservado.
  - Material com divergência crítica fica bloqueado para novas requisições e novas autorizações.
  - Requisições já autorizadas continuam existindo.
- **Entregáveis:**
  - Indicador de divergência crítica no material/estoque.
  - Bloqueio na criação e autorização.
  - Mensagens claras para usuários.
- **Testes esperados:**
  - Marcar divergência crítica.
  - Bloquear nova requisição.
  - Bloquear nova autorização.
- **Critérios de aceite relacionados:** 7.3, 8.8, 2.11

### MVP-BE-EST-002 — Implementar resolução automática de divergência crítica

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** MVP-BE-EST-001
- **Objetivo:** remover divergência quando saldo físico voltar a ser maior ou igual ao saldo reservado.
- **Regras de negócio:**
  - Resolução pode ocorrer por cancelamentos, atendimentos parciais, estornos ou nova importação CSV.
  - Quando resolvida, material volta a permitir requisições e autorizações se tiver saldo disponível.
- **Entregáveis:**
  - Recalculo automático após operações que alterem saldo físico/reservado.
  - Remoção de pendência de gestão.
- **Testes esperados:**
  - Resolver divergência após saldo físico >= reservado.
  - Manter bloqueio enquanto físico < reservado.
- **Critérios de aceite relacionados:** 7.4

### MVP-FS-MAT-001 — Implementar tela de detalhe do material

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-MAT-002, PIL-BE-EST-001, PIL-BE-AUD-003
- **Objetivo:** permitir consulta operacional do material.
- **Regras de negócio:**
  - Exibir código, nome, descrição, grupo, subgrupo, unidade, status, saldo físico, saldo reservado, saldo disponível, divergência crítica e históricos.
  - Observações internas são o único campo textual editável localmente.
- **Entregáveis:**
  - Tela de detalhe do material.
  - Exibição de saldos e histórico.
  - Edição de observações internas por Almoxarifado.
- **Testes esperados:**
  - Visualizar saldos.
  - Editar observação interna.
  - Não editar campos oficiais do SCPI.
- **Critérios de aceite relacionados:** 7.1, 7.2

### MVP-BE-MAT-001 — Implementar inativação de material

- **Fase:** MVP completo
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** MVP-FS-MAT-001
- **Objetivo:** permitir inativação controlada de materiais.
- **Regras de negócio:**
  - Apenas chefe de almoxarifado ou superusuário podem inativar.
  - Material só pode ser inativado com saldo físico zero e saldo reservado zero.
  - Material inativo permanece em históricos e relatórios antigos.
- **Entregáveis:**
  - Ação de inativação.
  - Bloqueio por saldo físico ou reservado.
  - Testes de permissão.
- **Testes esperados:**
  - Inativar material sem saldo.
  - Bloquear material com saldo físico.
  - Bloquear material com saldo reservado.
- **Critérios de aceite relacionados:** 7.5, 7.6

## 4.2.3 Épico 3 — Requisições

### MVP-BE-REQ-001 — Completar cancelamento de requisição autorizada

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** PIL-BE-AUT-005
- **Objetivo:** permitir cancelamento de requisição autorizada com liberação de reserva.
- **Regras de negócio:**
  - Criador, beneficiário, funcionário do Almoxarifado ou chefe de Almoxarifado podem cancelar requisição autorizada.
  - Justificativa é obrigatória.
  - Cancelamento libera reservas e não altera saldo físico.
- **Entregáveis:**
  - Ação de cancelamento autorizada.
  - Movimentação de liberação de reserva por cancelamento.
  - Registro na linha do tempo.
  - Notificação ao criador e beneficiário sobre o cancelamento.
- **Testes esperados:**
  - Cancelar autorizada com justificativa.
  - Bloquear sem justificativa.
  - Confirmar liberação de reserva.
  - Notificar criador e beneficiário.
- **Critérios de aceite relacionados:** 1.11, 9.5

### MVP-BE-REQ-002 — Implementar bloqueio de cancelamento após atendimento ou estorno

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Backend / Frontend
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** impedir cancelamento de requisições encerradas operacionalmente.
- **Regras de negócio:**
  - Requisições `atendidas`, `atendidas parcialmente` ou `estornadas` não podem ser canceladas.
  - Interface não deve exibir ação de cancelamento nesses estados.
- **Entregáveis:**
  - Bloqueio no backend.
  - Remoção/ocultação da ação no frontend.
- **Testes esperados:**
  - Backend bloqueia cancelamento.
  - Frontend não mostra botão.
- **Critérios de aceite relacionados:** 1.12, 6.3

### MVP-BE-REQ-003 — Implementar correção e reenvio de requisição recusada

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-AUT-004, PIL-BE-REQ-007
- **Objetivo:** permitir que criador ou beneficiário corrijam e reenviem requisição recusada.
- **Regras de negócio:**
  - Requisição recusada pode ser corrigida e reenviada.
  - Ação cabe ao criador ou beneficiário.
  - Reenvio retorna para `aguardando autorização`.
- **Entregáveis:**
  - Fluxo de edição de recusada.
  - Ação de reenviar.
  - Registro de correção/reenvio na linha do tempo.
- **Testes esperados:**
  - Corrigir recusada.
  - Reenviar recusada.
  - Bloquear usuário sem permissão.
- **Critérios de aceite relacionados:** 2.6

### MVP-FS-REQ-004 — Implementar cópia de requisição atendida ou atendida parcialmente

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-REQ-003, PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** facilitar pedidos recorrentes copiando requisições encerradas.
- **Regras de negócio:**
  - Só copiar requisições `atendidas` ou `atendidas parcialmente`.
  - Copiar apenas quantidades originalmente solicitadas.
  - Não copiar quantidades autorizadas nem entregues.
  - Gerar novo rascunho sem número público até o primeiro envio, com novo criador e nova data.
  - Recalcular saldo disponível atual.
  - Itens sem saldo ou com divergência crítica não devem ser copiados automaticamente.
- **Entregáveis:**
  - Ação de copiar requisição.
  - Tela/feedback de itens não copiados.
  - Validações de beneficiário permitido.
- **Testes esperados:**
  - Copiar atendida.
  - Bloquear cópia de status não permitido.
  - Não copiar item sem saldo.
  - Não manter beneficiário sem permissão.
- **Critérios de aceite relacionados:** 1.13

## 4.2.4 Épico 4 — Autorizações

### MVP-BE-AUT-001 — Bloquear autorização de material com divergência crítica

- **Fase:** MVP completo
- **Tipo:** Backend
- **Agente sugerido:** Agente backend de regras de estoque
- **Depende de:** MVP-BE-EST-001
- **Objetivo:** impedir autorização de item problemático.
- **Regras de negócio:**
  - Material com divergência crítica ativa não pode receber nova autorização.
  - Sistema deve orientar que a divergência seja resolvida.
- **Entregáveis:**
  - Validação na autorização.
  - Mensagem clara ao chefe.
- **Testes esperados:**
  - Bloquear item com divergência crítica.
  - Permitir após resolução da divergência.
- **Critérios de aceite relacionados:** 2.11, 7.3, 7.4

### MVP-TEST-AUT-002 — Completar testes automatizados de autorização

- **Fase:** MVP completo
- **Tipo:** Testes
- **Agente sugerido:** Agente de testes
- **Depende de:** PIL-BE-AUT-003, PIL-BE-AUT-004, PIL-BE-AUT-006, MVP-BE-AUT-001
- **Objetivo:** garantir cobertura dos cenários críticos de autorização.
- **Regras de negócio:**
  - Cobrir autorização total, parcial, item zerado, todos os itens zerados, recusa, saldo alterado e concorrência.
- **Entregáveis:**
  - Testes automatizados de integração/unidade.
  - Casos de concorrência documentados.
- **Testes esperados:**
  - Critérios 2.1 a 2.11 cobertos.
- **Critérios de aceite relacionados:** 2.1 a 2.11

## 4.2.5 Épico 5 — Atendimento pelo Almoxarifado

### MVP-TEST-ATE-001 — Completar testes automatizados de atendimento

- **Fase:** MVP completo
- **Tipo:** Testes
- **Agente sugerido:** Agente de testes
- **Depende de:** PIL-BE-ATE-003, PIL-BE-ATE-004, PIL-BE-ATE-005, PIL-BE-ATE-006
- **Objetivo:** garantir cobertura dos cenários críticos de atendimento.
- **Regras de negócio:**
  - Cobrir atendimento completo, parcial, entrega zero, item autorizado zero, saldo físico insuficiente e atendimento sem entrega.
- **Entregáveis:**
  - Testes automatizados de atendimento.
  - Casos de estoque e reserva validados.
- **Testes esperados:**
  - Critérios 3.1 a 3.9 cobertos.
- **Critérios de aceite relacionados:** 3.1 a 3.9

## 4.2.6 Épico 6 — Devoluções, saídas excepcionais e estornos

### MVP-BE-DEV-001 — Implementar devolução vinculada a requisição

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Estoque
- **Agente sugerido:** Agente fullstack de estoque
- **Depende de:** PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** registrar entrada por devolução vinculada a requisição atendida ou atendida parcialmente.
- **Regras de negócio:**
  - Devolução deve estar vinculada a requisição atendida ou atendida parcialmente.
  - Justificativa ou observação é obrigatória.
  - Devolução aumenta saldo físico.
  - Devolução não altera status da requisição original.
  - Total devolvido por item não pode ultrapassar quantidade efetivamente entregue.
- **Entregáveis:**
  - Modelo/tabela de devolução.
  - Ação/tela de registrar devolução.
  - Movimentação de entrada por devolução.
  - Controle de total devolvido por item.
- **Testes esperados:**
  - Registrar devolução válida.
  - Bloquear devolução sem requisição válida.
  - Bloquear devolução acima da quantidade entregue.
- **Critérios de aceite relacionados:** 4.1 a 4.4

### MVP-BE-SAI-001 — Implementar saída excepcional

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Estoque
- **Agente sugerido:** Agente fullstack de estoque
- **Depende de:** MVP-BE-ACE-001, PIL-BE-EST-001
- **Objetivo:** permitir baixa de estoque fora de requisição em situações excepcionais.
- **Regras de negócio:**
  - Apenas chefe de almoxarifado pode registrar.
  - Tipos: perda, vencimento, quebra, descarte, doação e empréstimo a outros órgãos.
  - Justificativa textual obrigatória.
  - Saída não pode ultrapassar saldo disponível.
  - Empréstimo a outros órgãos é saída definitiva no MVP.
- **Entregáveis:**
  - Modelo/tabela de saída excepcional.
  - Tela/endpoint de registro.
  - Movimentação de saída excepcional.
  - Validação de saldo disponível.
- **Testes esperados:**
  - Registrar saída válida.
  - Bloquear usuário sem permissão.
  - Bloquear sem justificativa.
  - Bloquear acima do saldo disponível.
- **Critérios de aceite relacionados:** 5.1 a 5.4

### MVP-BE-ESTOR-001 — Implementar estorno de requisição atendida

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Estoque
- **Agente sugerido:** Agente fullstack de estoque
- **Depende de:** PIL-BE-ATE-003, PIL-BE-ATE-004
- **Objetivo:** permitir estorno total ou parcial de requisições atendidas.
- **Regras de negócio:**
  - Apenas chefe de almoxarifado pode estornar.
  - Justificativa obrigatória.
  - Estorno devolve saldo físico.
  - Requisição passa para `estornada`.
  - Requisição estornada não pode ser corrigida, reenviada, atendida ou cancelada.
- **Entregáveis:**
  - Modelo/tabela de estorno.
  - Ação/tela de estorno.
  - Movimentação de estorno.
  - Bloqueio visual de ações após estorno.
- **Testes esperados:**
  - Estornar total.
  - Estornar parcial.
  - Bloquear usuário sem permissão.
  - Bloquear ações após estorno.
- **Critérios de aceite relacionados:** 6.1, 6.2, 6.3

### MVP-BE-ESTOR-002 — Implementar estorno de saída excepcional

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** MVP-BE-SAI-001, MVP-BE-ESTOR-001
- **Objetivo:** permitir reversão total ou parcial de saída excepcional.
- **Regras de negócio:**
  - Apenas chefe de almoxarifado pode estornar.
  - Justificativa obrigatória.
  - Deve preservar saída original no histórico.
  - Deve devolver saldo físico na quantidade estornada.
- **Entregáveis:**
  - Ação de estorno de saída excepcional.
  - Movimentação de estorno.
  - Status da saída como ativa ou estornada.
- **Testes esperados:**
  - Estornar saída total.
  - Estornar saída parcial.
  - Preservar histórico original.
- **Critérios de aceite relacionados:** 6.4

### MVP-BE-ESTOR-003 — Implementar estorno de devolução

- **Fase:** MVP completo
- **Tipo:** Backend / Estoque
- **Agente sugerido:** Agente backend de estoque
- **Depende de:** MVP-BE-DEV-001, MVP-BE-ESTOR-001
- **Objetivo:** permitir correção de devolução registrada por engano.
- **Regras de negócio:**
  - Apenas chefe de almoxarifado pode estornar.
  - Justificativa obrigatória.
  - Estorno de devolução reduz saldo físico.
  - Só pode ocorrer se houver saldo disponível suficiente.
- **Entregáveis:**
  - Ação de estorno de devolução.
  - Validação de saldo disponível.
  - Movimentação de estorno.
- **Testes esperados:**
  - Estornar devolução com saldo disponível.
  - Bloquear quando saldo já foi reservado ou consumido.
- **Critérios de aceite relacionados:** 6.5, 6.6

## 4.2.7 Épico 7 — Notificações

### MVP-BE-NOT-001 — Implementar resolução automática de notificações

- **Fase:** MVP completo
- **Tipo:** Backend
- **Agente sugerido:** Agente backend
- **Depende de:** PIL-BE-NOT-001, PIL-BE-NOT-002
- **Objetivo:** resolver notificações quando a ação relacionada perder sentido.
- **Regras de negócio:**
  - Notificação de autorização pendente deve ser resolvida se a requisição for retornada para rascunho, cancelada ou resolvida por outra ação.
  - Histórico real da operação deve permanecer preservado.
- **Entregáveis:**
  - Campo/status de resolução.
  - Gatilhos de resolução por evento.
- **Testes esperados:**
  - Resolver notificação ao cancelar requisição.
  - Resolver notificação ao retornar para rascunho.
- **Critérios de aceite relacionados:** 9.6

### MVP-BE-NOT-002 — Implementar expiração e ocultação de notificações lidas

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Backend / Frontend
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-FS-NOT-003
- **Objetivo:** completar ciclo de vida das notificações.
- **Regras de negócio:**
  - Notificações não lidas não devem expirar rapidamente.
  - Notificações lidas podem expirar após 7 dias.
  - Usuário pode apagar/ocultar notificações lidas.
- **Entregáveis:**
  - Rotina de expiração.
  - Ação de ocultar/apagar notificação lida.
  - Testes de expiração.
- **Testes esperados:**
  - Lida expira após 7 dias.
  - Não lida permanece.
  - Usuário oculta lida.
- **Critérios de aceite relacionados:** 9.7

## 4.2.8 Épico 8 — Relatórios e painéis

### MVP-FS-PAI-001 — Implementar painel Gestão do Almoxarifado

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack
- **Agente sugerido:** Agente fullstack
- **Depende de:** MVP-BE-EST-001, MVP-BE-DEV-001, MVP-BE-SAI-001, MVP-BE-ESTOR-001
- **Objetivo:** agrupar ações sensíveis e pendências de gestão.
- **Regras de negócio:**
  - Visível para chefe de almoxarifado e superusuário conforme permissões.
  - Deve exibir divergências críticas como pendências/alertas.
  - Deve dar acesso às rotinas de saídas excepcionais, estornos, devoluções, importações CSV, histórico de importações e relatórios gerais, sempre respeitando as permissões do papel autenticado.
  - O superusuário pode acessar o painel para suporte técnico, consulta, importações CSV, histórico de importações e relatórios permitidos, mas não deve registrar retirada, devolução, saída excepcional ou estorno operacional.
- **Entregáveis:**
  - Tela de Gestão do Almoxarifado.
  - Cards/listas de pendências.
  - Links para rotinas do MVP completo.
- **Testes esperados:**
  - Chefe de almoxarifado acessa painel.
  - Superusuário acessa apenas rotinas compatíveis com suporte técnico/administração.
  - Superusuário não consegue executar ações operacionais de estoque pelo painel.
  - Usuário sem permissão é bloqueado.
  - Divergência crítica aparece e desaparece quando resolvida.
- **Critérios de aceite relacionados:** 7.3, 7.4, 8.8

### MVP-FS-REL-001 — Implementar relatório de estoque atual

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** PIL-BE-EST-001, MVP-BE-EST-001
- **Objetivo:** permitir consulta do estoque atual.
- **Regras de negócio:**
  - Exibir código, nome, grupo, subgrupo, unidade, saldo físico, reservado, disponível, status, divergência crítica, última atualização via SCPI e última movimentação.
  - Permitir filtros por grupo, subgrupo, ativo/inativo, somente com saldo disponível, somente com divergência crítica e busca por código ou nome.
- **Entregáveis:**
  - Endpoint de relatório.
  - Tela com filtros.
  - Exportação CSV respeitando filtros.
- **Testes esperados:**
  - Filtrar por grupo.
  - Filtrar divergência crítica.
  - Exportar CSV filtrado.
- **Critérios de aceite relacionados:** 10.1, 10.2, 10.3

### MVP-FS-REL-002 — Implementar histórico de movimentações por material

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** PIL-BE-AUD-003
- **Objetivo:** consultar movimentações detalhadas de um material.
- **Regras de negócio:**
  - Exibir entradas, saídas, reservas, liberações, devoluções, estornos e atualizações via SCPI.
  - Permitir filtros por período, tipo, origem e usuário responsável.
- **Entregáveis:**
  - Endpoint de histórico.
  - Tela de consulta.
  - Exportação CSV.
- **Testes esperados:**
  - Listar movimentações de material.
  - Filtrar por tipo.
  - Exportar CSV.
- **Critérios de aceite relacionados:** 10.1, 10.2

### MVP-FS-REL-003 — Implementar relatório de consumo por setor

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** PIL-BE-ATE-003, MVP-BE-DEV-001, MVP-BE-ESTOR-001
- **Objetivo:** mostrar consumo de materiais por setor em determinado período.
- **Regras de negócio:**
  - Consumo considera apenas quantidade efetivamente entregue.
  - Devoluções e estornos abatem do consumo.
  - Atendimentos parciais contam apenas quantidade entregue.
- **Entregáveis:**
  - Endpoint de relatório.
  - Tela com filtros por período, setor, grupo, subgrupo e material.
  - Exportação CSV.
- **Testes esperados:**
  - Calcular consumo entregue.
  - Abater devolução.
  - Abater estorno.
- **Critérios de aceite relacionados:** 10.1, 10.2, 10.4

### MVP-FS-REL-004 — Implementar relatório de consumo por material

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** MVP-FS-REL-003
- **Objetivo:** mostrar materiais mais consumidos em determinado período.
- **Regras de negócio:**
  - Consumo considera apenas quantidade efetivamente entregue.
  - Devoluções e estornos abatem do consumo.
  - Deve permitir ordenar por maior consumo.
- **Entregáveis:**
  - Endpoint de relatório.
  - Tela com filtros e ordenação.
  - Exportação CSV.
- **Testes esperados:**
  - Ordenar por maior consumo.
  - Filtrar por período e material.
- **Critérios de aceite relacionados:** 10.1, 10.2, 10.4

### MVP-FS-REL-005 — Implementar relatório de requisições por status

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** PIL-BE-REQ-001
- **Objetivo:** acompanhar requisições por status e filtros operacionais.
- **Regras de negócio:**
  - Chefe de setor vê apenas requisições do próprio setor.
  - Funcionários do Almoxarifado e chefe de Almoxarifado veem todos os setores.
  - Solicitante comum não acessa relatório geral.
  - Rascunhos nunca enviados podem aparecer sem número público; requisições já enviadas devem exibir o número público preservado.
  - Valor total não entra no MVP.
- **Entregáveis:**
  - Endpoint de relatório.
  - Tela com filtros por status, período, setor, beneficiário, criador, material e chefe.
  - Exportação CSV.
- **Testes esperados:**
  - Filtrar por status.
  - Respeitar permissão por perfil.
  - Exportar CSV.
- **Critérios de aceite relacionados:** 10.1, 10.2

### MVP-FS-REL-006 — Implementar relatório de saídas fora de requisição

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack de relatórios
- **Depende de:** MVP-BE-SAI-001, MVP-BE-ESTOR-002
- **Objetivo:** listar saídas excepcionais e seus estornos.
- **Regras de negócio:**
  - Visível para funcionários do Almoxarifado, chefe de Almoxarifado e superusuário.
  - Chefe de setor não acessa esse relatório no MVP.
  - Deve permitir filtros por período, tipo, material, grupo, subgrupo, responsável, somente estornadas e somente não estornadas.
- **Entregáveis:**
  - Endpoint de relatório.
  - Tela com filtros.
  - Exportação CSV.
- **Testes esperados:**
  - Listar saídas.
  - Filtrar estornadas.
  - Bloquear chefe de setor.
- **Critérios de aceite relacionados:** 10.1, 10.2

### MVP-FS-REL-007 — Implementar histórico de importações CSV

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Fullstack / Relatórios
- **Agente sugerido:** Agente fullstack
- **Depende de:** MVP-BE-IMP-002
- **Objetivo:** permitir consulta técnica das importações realizadas.
- **Regras de negócio:**
  - Superusuário acessa histórico completo.
  - Chefe de almoxarifado pode consultar.
  - Tela deve exibir totais, erros, alertas, divergências e status.
- **Entregáveis:**
  - Registro persistente de importações.
  - Tela de histórico.
  - Filtros básicos se aplicável.
- **Testes esperados:**
  - Registrar importação concluída.
  - Registrar importação com alertas.
  - Registrar importação falha.
- **Critérios de aceite relacionados:** 8.9

## 4.2.9 Épico 9 — Auditoria, histórico e rastreabilidade

### MVP-BE-AUD-001 — Completar linha do tempo da requisição

- **Status atual:** postergada fora do escopo ativo de backend/API.

- **Fase:** MVP completo
- **Tipo:** Backend / Frontend
- **Agente sugerido:** Agente fullstack
- **Depende de:** PIL-BE-AUD-001, PIL-FE-AUD-002
- **Objetivo:** incluir todos os eventos operacionais previstos na linha do tempo.
- **Regras de negócio:**
  - Incluir criação, envio, retorno para rascunho, reenvio, recusa, autorização, cancelamento, atendimento, devolução e estorno.
  - Rascunhos nunca enviados não precisam gerar linha do tempo operacional formal.
  - A linha do tempo operacional deve ser preservada a partir do primeiro envio para autorização, quando a requisição recebe número público.
  - Mostrar data/hora, usuário, ação e justificativa/observação.
  - Eventos não devem ser escondidos de usuários autorizados.
- **Entregáveis:**
  - Eventos completos no backend.
  - Exibição completa na interface.
- **Testes esperados:**
  - Cada transição relevante gera evento.
  - Linha do tempo exibe justificativas.
- **Critérios de aceite relacionados:** 1.6, 1.7, 1.11, 3.9, 4.1, 6.1

### MVP-BE-AUD-002 — Garantir preservação de registros operacionais

- **Fase:** MVP completo
- **Tipo:** Backend / Testes
- **Agente sugerido:** Agente backend de auditoria
- **Depende de:** MVP-BE-AUD-001
- **Objetivo:** impedir exclusão direta de registros operacionais relevantes.
- **Regras de negócio:**
  - Registros operacionais relevantes não devem ser excluídos diretamente.
  - Rascunhos nunca enviados para autorização podem ser descartados/excluídos, pois ainda não são registros operacionais formais.
  - Requisições já numeradas, inclusive se retornarem para rascunho, não devem ser excluídas diretamente.
  - Correções devem ocorrer por estorno, reimportação CSV ou inativação, conforme o caso.
- **Entregáveis:**
  - Bloqueios de exclusão.
  - Soft delete apenas onde permitido.
  - Testes de proteção.
- **Testes esperados:**
  - Impedir exclusão de movimentação.
  - Impedir exclusão de requisição operacional encerrada.
  - Permitir descarte de rascunho nunca enviado.
  - Impedir exclusão física de requisição já numerada.
- **Critérios de aceite relacionados:** 6.1, 6.3

## 4.2.10 Épico 10 — Piloto e implantação gradual

### MVP-DOC-IMP-001 — Consolidar aprendizados do piloto

- **Fase:** MVP completo
- **Tipo:** Implantação / Documentação
- **Agente sugerido:** Agente de implantação
- **Depende de:** execução do piloto
- **Objetivo:** transformar problemas reais do piloto em ajustes do MVP completo.
- **Regras de negócio:**
  - Ajustes não devem ampliar escopo sem passar pela separação Piloto/MVP/Pós-MVP.
  - Mudanças de regra devem atualizar documentação e critérios de aceite.
- **Entregáveis:**
  - Lista de problemas reais.
  - Decisões de ajuste.
  - Tarefas novas ou alteradas no backlog.
- **Testes esperados:**
  - Validar critérios de sucesso antes da expansão.
- **Critérios de aceite relacionados:** critérios de sucesso do MVP em `docs/design-acesso-ocasional/mvp-plano-implantacao.md`

### MVP-DOC-IMP-002 — Planejar expansão gradual de materiais e setores

- **Fase:** MVP completo
- **Tipo:** Implantação
- **Agente sugerido:** Agente de implantação
- **Depende de:** MVP-DOC-IMP-001
- **Objetivo:** planejar liberação gradual para materiais e rotinas mais complexas.
- **Regras de negócio:**
  - Expansão só deve ocorrer após critérios de sucesso do piloto.
  - Rotinas complementares devem ser liberadas de forma controlada.
- **Entregáveis:**
  - Plano de expansão.
  - Ordem de inclusão de categorias de materiais.
  - Critérios de liberação por etapa.
- **Testes esperados:**
  - Checklist de prontidão por etapa.
- **Critérios de aceite relacionados:** critérios de sucesso do MVP em `docs/design-acesso-ocasional/mvp-plano-implantacao.md`

## 4.3 Pós-MVP

Objetivo: registrar funcionalidades futuras que não devem entrar no piloto nem no MVP completo.

Itens pós-MVP:

- Ajuste manual de estoque no ERP-SAEP.
- Conversão de unidades de medida.
- Edição manual dos dados cadastrais de materiais provenientes do SCPI.
- Cadastro e uso operacional de localização física de prateleiras.
- Inventário/conferência física formal.
- Modelos ou favoritos de requisição.
- Aplicativo mobile dedicado.
- Notificações por e-mail.
- Exportação de relatórios em PDF ou XLSX.
- Relatório específico de devoluções.
- Relatórios avançados, como consumo por grupo/subgrupo, requisições por funcionário/beneficiário e importações por período.
- Importação de campos financeiros do SCPI.
- Importação de preço médio.
- Importação de código de barras.
- Importação de local físico.
- Importação de estoque mínimo e máximo.
- Sincronização automática com SCPI.
- Tela avançada de conciliação bidirecional.

## 5. Ordem sugerida de implementação para agentes

### Fase 4 — Consolidação do MVP completo

1. MVP-BE-ACE-001 — Completar permissões de todos os papéis.
2. MVP-BE-ACE-002 — Implementar administração de usuários, setores e perfis pelo superusuário.
3. MVP-BE-IMP-001 — Implementar importação CSV via interface com pré-visualização.
4. MVP-BE-IMP-002 — Implementar aplicação transacional e regra tudo ou nada.
5. MVP-BE-IMP-003 — Implementar atualização de saldo físico via QUAN3 em reimportações.
6. MVP-BE-IMP-004 — Implementar materiais ausentes no CSV.
7. MVP-BE-EST-001 — Implementar divergência crítica de material.
8. MVP-BE-EST-002 — Implementar resolução automática de divergência crítica.
9. MVP-FS-MAT-001 — Implementar tela de detalhe do material.
10. MVP-BE-MAT-001 — Implementar inativação de material.
11. MVP-BE-REQ-001 — Completar cancelamento de requisição autorizada.
12. MVP-BE-REQ-002 — Implementar bloqueio de cancelamento após atendimento ou estorno.
13. MVP-BE-REQ-003 — Implementar correção e reenvio de requisição recusada.
14. MVP-FS-REQ-004 — Implementar cópia de requisição atendida ou atendida parcialmente.
15. MVP-BE-AUT-001 — Bloquear autorização de material com divergência crítica.
16. MVP-TEST-AUT-002 — Completar testes automatizados de autorização.
17. MVP-TEST-ATE-001 — Completar testes automatizados de atendimento.
18. MVP-BE-DEV-001 — Implementar devolução vinculada a requisição.
19. MVP-BE-SAI-001 — Implementar saída excepcional.
20. MVP-BE-ESTOR-001 — Implementar estorno de requisição atendida.
21. MVP-BE-ESTOR-002 — Implementar estorno de saída excepcional.
22. MVP-BE-ESTOR-003 — Implementar estorno de devolução.
23. MVP-BE-NOT-001 — Implementar resolução automática de notificações.
24. MVP-BE-NOT-002 — Implementar expiração e ocultação de notificações lidas.
25. MVP-BE-AUD-001 — Completar linha do tempo da requisição.
26. MVP-BE-AUD-002 — Garantir preservação de registros operacionais.

### Fase 5 — Relatórios e expansão

1. MVP-FS-PAI-001 — Implementar painel Gestão do Almoxarifado.
2. MVP-FS-REL-001 — Implementar relatório de estoque atual.
3. MVP-FS-REL-002 — Implementar histórico de movimentações por material.
4. MVP-FS-REL-003 — Implementar relatório de consumo por setor.
5. MVP-FS-REL-004 — Implementar relatório de consumo por material.
6. MVP-FS-REL-005 — Implementar relatório de requisições por status.
7. MVP-FS-REL-006 — Implementar relatório de saídas fora de requisição.
8. MVP-FS-REL-007 — Implementar histórico de importações CSV.
9. MVP-DOC-IMP-001 — Consolidar aprendizados do piloto.
10. MVP-DOC-IMP-002 — Planejar expansão gradual de materiais e setores.
