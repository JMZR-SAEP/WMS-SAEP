# Matriz de Invariantes — ERP-SAEP

## 1. Objetivo

Referência rápida dos invariantes que não podem ser violados por `models`, `services`, `policies`, endpoints, comandos, admin actions, importações ou interfaces futuras.

Fontes completas: `docs/design-acesso-ocasional/modelo-dominio-regras.md`, `processos-almoxarifado.md`, `criterios-aceite.md`, `importacao-scpi-csv.md`, `docs/design-acesso-rapido/api-contracts.md` e `docs/code-review-guidelines.md`.

## 2. Como usar

Para cada mudança, localizar o invariante aplicável, implementar na camada indicada, reforçar com constraint/policy/service quando couber e cobrir teste de caminho feliz, permissão negada e violação de domínio. Mudanças de endpoint também exigem contrato OpenAPI e envelope de erro.

## 3. Matriz compacta

| ID | Tema | Invariante | Camada/reforço esperado | Testes mínimos | Ref. |
|---|---|---|---|---|---|
| USR-01 | Usuários | Login por matrícula funcional única. | Model/Auth; unicidade e autenticação por matrícula. | Login válido; duplicidade; matrícula inválida. | Modelo 2.1 |
| USR-02 | Usuários | CPF e telefone não são cadastro permanente. | Model/importação; uso transitório do CPF só para senha inicial. | Campos ausentes; importação não retém CPF/telefone. | Modelo 2.1 |
| USR-03 | Usuários | Usuário inativo não acessa nem opera. | Auth/policy. | Login bloqueado; escrita negada. | Crit. 11.1 |
| USR-04 | Usuários | Todo usuário ativo é solicitante. | Policy derivada de usuário ativo. | Criar para si; negar operação fora do papel. | Crit. 11.1 |
| USR-05 | Setores | Usuário pertence a um único setor. | Model; FK de setor principal. | Criar com setor; sem vínculos auxiliares. | Modelo 2.1 |
| USR-06 | Setores | Todo setor tem chefe e não fica sem chefe. | Model/service; validação em alteração. | Criar com chefe; bloquear sem chefe. | Backlog ACE-002 |
| USR-07 | Setores | Um chefe responde por apenas um setor. | Constraint/policy. | Bloquear chefe duplicado. | Modelo 2.1 |
| USR-08 | Setores | Setor inativo permanece em histórico e não recebe nova requisição. | Service/policy; preservar FK histórica. | Negar nova requisição; histórico visível. | Modelo 2.1 |
| PER-01 | Permissões | Solicitante cria apenas para si. | Policy/service compartilhados. | Próprio permitido; terceiro negado. | Crit. 11.1 |
| PER-02 | Permissões | Auxiliar de setor atua apenas no próprio setor. | Policy por setor principal. | Mesmo setor permitido; outro negado. | Crit. 11.2 |
| PER-03 | Permissões | Chefe autoriza só setor do beneficiário. | Policy por setor responsável. | Próprio setor permitido; outro negado. | Crit. 2.1 |
| PER-04 | Permissões | Almoxarifado cria em nome de qualquer funcionário. | Policy de papel operacional. | Criar para setores distintos. | Crit. 1.1 |
| PER-05 | Permissões | Chefe de Almoxarifado herda auxiliar de Almoxarifado. | Composição explícita de permissões. | Atendimento/devolução como chefe; autorização só do setor Almoxarifado. | Crit. 11.5 |
| PER-06 | Permissões | Superusuário é suporte/admin, não operador cotidiano de estoque. | Policy/admin. | Permitir importação/cadastros; negar retirada/devolução/saída/estorno. | Crit. 11.6 |
| PER-07 | Permissões | Requisição pertence ao setor do beneficiário, não do criador. | Service/model snapshot. | Almoxarifado cria para Obras e vai ao chefe de Obras. | Crit. 1.2 |
| PER-08 | Permissões | Views e services chamam a mesma policy contextual. | `policies.py` ou equivalente. | View e service negam mesmo escopo. | API, CodeRabbit |
| REQ-01 | Requisições | Toda requisição começa em rascunho. | Service/model default. | Criação gera `rascunho`. | Crit. 1.1 |
| REQ-02 | Requisições | Rascunho nunca enviado não tem número público. | Service/model; número nulo até envio. | Criar sem número; descartar sem consumir número. | Crit. 1.9 |
| REQ-03 | Requisições | Número público nasce no primeiro envio e segue `REQ-AAAA-NNNNNN`. | Gerador anual atômico. | Formato e sequência anual. | Crit. 1.6 |
| REQ-04 | Requisições | Reenvios preservam número público. | Campo histórico imutável. | Retorno e reenvio mantêm número. | Crit. 1.7 |
| REQ-05 | Requisições | Requisição precisa ter ao menos um item. | Serializer + regra crítica no service. | Bloquear criar/salvar/enviar sem item. | Crit. 1.1 |
| REQ-06 | Requisições | Após envio, não há edição direta de itens. | Máquina de estados/service. | Bloquear edição; permitir retorno para rascunho. | Crit. 1.8 |
| REQ-07 | Requisições | Registrar criador, beneficiário e setor do beneficiário. | Campos obrigatórios/snapshots. | Criar em nome de terceiro preservando papéis. | Crit. 1.1 |
| REQ-08 | Requisições | Timeline registra eventos principais e é visível a autorizados. | Service/API/policy. | Eventos do ciclo; autorizado vê completa; fora de escopo não vê. | Modelo 2.1 |
| REQ-09 | Requisições | Cópia recalcula saldo e não copia autorizado/entregue. | Service de cópia. | Copiar atendida/parcial; bloquear item sem saldo/divergente. | Crit. 1.13 |
| ITEM-01 | Itens | Quantidade autorizada nunca maior que solicitada. | Service/constraint. | Bloquear autorização acima. | Crit. 2 |
| ITEM-02 | Itens | Quantidade entregue nunca maior que autorizada. | Service/constraint. | Bloquear entrega acima. | Crit. 3 |
| ITEM-03 | Itens | Autorização parcial exige justificativa. | Service/serializer. | Menor com justificativa; sem justificativa negado. | Crit. 2.3 |
| ITEM-04 | Itens | Atendimento parcial exige justificativa. | Service/serializer. | Menor com justificativa; sem justificativa negado. | Crit. 3.3 |
| ITEM-05 | Itens | Item autorizado com zero exige justificativa. | Service/serializer. | Zero com justificativa; sem justificativa negado. | Crit. 2.4 |
| ITEM-06 | Itens | Entrega zero exige justificativa quando havia autorização > 0. | Service/serializer. | Zero com justificativa; item autorizado zero não exige entrega. | Crit. 3.4 |
| ITEM-07 | Itens | Requisição autorizada precisa de item autorizado > 0. | Regra agregada no service. | Bloquear todos zerados; orientar recusa. | Crit. 2.5 |
| ITEM-08 | Itens | Requisição atendida/parcial precisa de item entregue > 0. | Regra agregada no service. | Bloquear finalização sem entrega; orientar cancelamento. | Crit. 3.6 |
| EST-01 | Estoque | Físico e reservado são armazenados; disponível = físico - reservado. | Model/service; disponível calculado. | Cálculo após reserva, retirada e liberação. | Crit. 7.2 |
| EST-02 | Estoque | Autorização reserva, mas não baixa físico. | Service + movimentação de reserva. | Reservado aumenta; físico mantém. | Crit. 2.2 |
| EST-03 | Estoque | Retirada consome reserva e baixa físico. | Service transacional. | Atendimento reduz físico e reservado. | Crit. 3.2 |
| EST-04 | Estoque | Reserva não entregue deve ser liberada. | Service transacional. | Atendimento parcial/cancelamento libera reserva. | Crit. 3.3 |
| EST-05 | Estoque | Não pode reservar acima do disponível. | Recalcular dentro do lock. | Bloqueio e concorrência entre autorizações. | Crit. 2.8-2.10 |
| EST-06 | Estoque | Operações críticas usam transação e lock. | `atomic()`, `select_for_update()`, locks determinísticos. | Teste PostgreSQL de concorrência/idempotência. | CodeRabbit |
| EST-07 | Estoque | Divergência crítica: físico < reservado. | Marcador/recalculo no service. | Importação reduz físico e marca divergência. | Crit. 7.3 |
| EST-08 | Estoque | Material divergente bloqueia novas requisições e autorizações. | Policy/service. | Bloquear criação e autorização. | Crit. 1.5, 2.11 |
| EST-09 | Estoque | Divergência resolve quando físico >= reservado. | Recalcular após operação/importação. | Remover alerta e liberar se houver disponível. | Crit. 7.4 |
| EST-10 | Estoque | Material inativo não entra em nova requisição. | Queryset/service. | Bloquear seleção; histórico preservado. | Crit. 7.1 |
| EST-11 | Estoque | Material só inativa com físico e reservado zerados. | Service/policy. | Permitir zerado; bloquear com saldo. | Crit. 7.5-7.6 |
| EST-12 | Estoque | Não há ajuste manual de estoque no MVP. | Sem endpoint/admin action; correção por SCPI/operação formal. | Tentativa negada se existir superfície. | Modelo 2.3 |
| AUD-01 | Auditoria | Movimentações de estoque são histórico/auditoria. | Ledger com saldo anterior/posterior e origem. | Gerar para reserva, saída, liberação, SCPI, devolução, estorno. | Modelo 2.3 |
| AUD-02 | Auditoria | Movimentações registradas não são editadas/excluídas diretamente. | Imutabilidade de ledger. | Bloquear update/delete; correção compensatória. | CodeRabbit |
| AUD-03 | Auditoria | Correções de requisições finalizadas ocorrem por estorno. | Service formal de estorno. | Estorno total/parcial; não reabre requisição. | Crit. 6 |
| AUD-04 | Auditoria | Timeline expõe eventos a usuários autorizados. | API/policy. | Autorizado vê; fora de escopo não vê. | Modelo 2.1 |
| AUD-05 | Auditoria | Side effects ocorrem após commit quando aplicável. | Eventos/`publish_on_commit()`. | Falha de notificação não desfaz operação; só após commit. | CodeRabbit |
| AUD-06 | Auditoria | Notificações não decidem sucesso da transação principal. | Side effect desacoplado. | Operação conclui sem depender de notificação. | CodeRabbit |
| SCPI-01 | SCPI CSV | SCPI é a fonte oficial para a carga inicial técnica de catálogo e saldo físico. | Import service/model. | Criar grupo, subgrupo, material e saldo inicial pelo CSV. | Importação 1 |
| SCPI-02 | SCPI CSV | ERP-SAEP não edita cadastro oficial vindo do SCPI. | Campos oficiais read-only. | Bloquear edição de nome, descrição, grupo, subgrupo, sequencial e unidade. | Modelo 2.1 |
| SCPI-03 | SCPI CSV | CSV aceito: UTF-8 com BOM e separador `;`. | Leitor configurado. | Arquivo válido lido corretamente. | Crit. 8.1 |
| SCPI-04 | SCPI CSV | Linha sem código continua o registro lógico anterior. | Normalizer de produto lógico. | Nome/descrição quebrados em múltiplas linhas viram um único material lógico. | Crit. 8.1 |
| SCPI-05 | SCPI CSV | Erro técnico impeditivo aplica tudo ou nada. | Transação na aplicação. | Falha técnica não persiste nada. | Crit. 8.3 |
| SCPI-06 | SCPI CSV | Parser deve normalizar entradas reais do SCPI antes de persistir. | Parser/service. | BOM, `;`, multiline e quantidade com vírgula decimal cobertos por teste. | PR #21 |
| SCPI-07 | SCPI CSV | Material duplicado na carga inicial não deve ser sobrescrito silenciosamente. | Service/model. | Duplicidade falha e aborta a transação. | PR #21 |
| SCPI-08 | SCPI CSV | `QUAN3` da carga inicial gera `SALDO_INICIAL` imutável. | Service + ledger. | Registrar estoque inicial e movimentação coerente. | PR #21 |
| SCPI-09 | SCPI CSV | Divergência por importação não cancela reservas. | Bloqueio futuro sem apagar reservas. | Físico < reservado mantém reservas e bloqueia novas ações. | Importação 8 |
| API-01 | API | Endpoints formais ficam em `/api/v1/`. | URLs versionadas. | Rotas formais sob `/api/v1/`. | API |
| API-02 | API | Endpoint declara auth, autorização, I/O, status, erros, paginação/filtros e OpenAPI. | View/schema/serializers. | Teste de contrato e schema. | API |
| API-03 | API | Serializer valida formato; service valida domínio crítico. | Views/serializers finos. | Payload inválido no serializer; domínio no service. | API |
| API-04 | API | Erros usam envelope padrão. | Handler global. | 400/401/403/404/409/500 no envelope. | API |
| API-05 | API | Conflito de domínio usa `409 domain_conflict`. | Exceção HTTP-safe. | Saldo, transição ou estado conflitante retornam 409. | API |
| API-06 | API | Listas usam paginação padrão. | Pagination class. | Envelope com `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, `results`. | API |

## 4. Notas por tema

- **Usuários/setores/papéis:** dados cadastrais definem escopo; permissões completas ficam em `matriz-permissoes.md`.
- **Requisições/itens:** estados e transições ficam em `estado-transicoes-requisicao.md`; este arquivo lista invariantes que não podem ser contornados.
- **Estoque:** qualquer mutação de saldo/reserva é transacional, auditável e recalcula disponibilidade no ponto crítico.
- **SCPI:** cadastro oficial e correção de físico vêm do SCPI; ERP-SAEP só registra observações internas e operações formais.
- **API:** contrato DRF é parte da entrega, não etapa posterior.

## 5. Checklist para PRs

- O PR altera invariante, permissão, status, saldo, reserva, auditoria ou contrato?
- A documentação rápida e completa afetada foi atualizada?
- Há testes de caminho feliz, permissão negada e violação de domínio?
- Há teste PostgreSQL quando envolve estoque/reserva/concorrência?
- OpenAPI e envelope de erro foram atualizados quando endpoint mudou?
