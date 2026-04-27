# Estados e Transições da Requisição — ERP-SAEP

## 1. Objetivo

Este documento consolida a máquina de estados das requisições do ERP-SAEP, reunindo estados, ações, atores, pré-condições, efeitos colaterais, eventos de timeline e movimentações de estoque relacionadas ao ciclo de vida da requisição.

A referência deve orientar a implementação futura em Django/DRF sem alterar as regras de negócio já definidas em `docs/design-acesso-ocasional/modelo-dominio-regras.md`, `docs/design-acesso-ocasional/processos-almoxarifado.md`, `docs/design-acesso-ocasional/criterios-aceite.md` e backlogs técnicos.

## 2. Princípios

- Usar máquina de estados declarativa como fonte única de verdade para transições permitidas.
- Não espalhar transições de status em blocos `if/elif` por views, serializers, admin actions, signals ou comandos.
- Services devem aplicar transições, validar regras de domínio e coordenar efeitos transacionais.
- Policies validam autorização contextual por usuário, papel, setor, beneficiário e estado da requisição.
- Transições que alteram estoque ou reserva devem usar transação atômica, lock pessimista nas linhas de estoque e ordem determinística de locks.
- Toda transição relevante gera evento de timeline visível a todos os usuários com permissão de visualizar a requisição.
- O status final deve ser derivado das ações executadas e das quantidades autorizadas e entregues.
- Notificações são side effects pós-transação, publicadas após commit quando aplicável, e nunca fonte de verdade do fluxo.

## 3. Estados canônicos

| Estado | Nome técnico sugerido | Descrição | Pode editar itens? | Pode gerar reserva? | Pode baixar estoque? | Estado final? |
|---|---|---|---|---|---|---|
| Rascunho | `rascunho` | Requisição criada, ainda não enviada ou retornada para correção. Rascunho nunca enviado não possui número público. | Sim, somente criador ou beneficiário. | Não. | Não. | Não. |
| Aguardando autorização | `aguardando_autorizacao` | Requisição enviada para análise do chefe do setor do beneficiário. No primeiro envio recebe número público. | Não. Deve retornar para rascunho antes de editar. | Não. | Não. | Não. |
| Recusada | `recusada` | Requisição inteira recusada pelo chefe do setor do beneficiário, com motivo obrigatório. | Sim, apenas no fluxo de correção pelo criador ou beneficiário antes do reenvio. | Não. | Não. | Não. |
| Autorizada | `autorizada` | Requisição aprovada total ou parcialmente e disponível para atendimento pelo Almoxarifado. | Não. | Sim, na entrada neste estado. | Não. | Não. |
| Atendida parcialmente | `atendida_parcialmente` | Pelo menos um item autorizado foi entregue abaixo da quantidade autorizada e ao menos um item teve entrega maior que zero. Encerra a requisição; não cria pendência automática. | Não. | Não. | Sim, na entrada neste estado. | Sim. |
| Atendida / finalizada | `atendida` | Todas as quantidades autorizadas foram entregues e a retirada foi registrada. | Não. | Não. | Sim, na entrada neste estado. | Sim. |
| Cancelada | `cancelada` | Requisição encerrada antes da retirada final, por descarte lógico ou cancelamento permitido. | Não. | Não. | Não. | Sim. |
| Estornada | `estornada` | Requisição atendida ou atendida parcialmente cuja saída foi revertida total ou parcialmente por estorno formal. | Não. | Não. | Sim, por movimentação inversa de estorno. | Sim. |

## 4. Eventos canônicos de timeline

| Evento | Nome técnico sugerido | Quando ocorre | Usuário responsável | Justificativa obrigatória? | Observações |
|---|---|---|---|---|---|
| Criação | `criacao` | Na criação do rascunho ou, no mínimo, na formalização do primeiro envio quando a requisição recebe número público. | Criador. | Não. | Rascunhos nunca enviados não precisam gerar timeline operacional formal. |
| Envio para autorização | `envio_autorizacao` | Quando o rascunho é enviado para análise. | Criador ou beneficiário. | Não. | Gera número público no primeiro envio e notifica o chefe do setor do beneficiário. |
| Retorno para rascunho | `retorno_rascunho` | Quando requisição em `aguardando_autorizacao` volta para correção. | Criador ou beneficiário. | Não. | Remove da fila de autorização e resolve notificação pendente. |
| Reenvio | `reenvio_autorizacao` | Quando requisição recusada ou retornada para rascunho é reenviada. | Criador ou beneficiário. | Não. | Preserva o número público já gerado. |
| Recusa | `recusa` | Quando o chefe recusa a requisição inteira. | Chefe do setor do beneficiário. | Sim. | Não há recusa individual por item no MVP. |
| Autorização total | `autorizacao_total` | Quando todos os itens são autorizados na quantidade solicitada. | Chefe do setor do beneficiário. | Não. | Cria reserva para itens autorizados. |
| Autorização parcial | `autorizacao_parcial` | Quando ao menos um item é autorizado com quantidade menor que a solicitada. | Chefe do setor do beneficiário. | Sim, por item parcial ou zerado. | Requisição autorizada deve ter ao menos um item com quantidade autorizada maior que zero. |
| Cancelamento | `cancelamento` | Quando a requisição é cancelada em estado permitido. | Criador, beneficiário, auxiliar de Almoxarifado ou chefe de Almoxarifado, conforme estado. | Obrigatória somente para cancelamento de autorizada. | Em autorizada, libera reservas. |
| Atendimento total | `atendimento_total` | Quando todas as quantidades autorizadas são entregues. | Auxiliar de Almoxarifado ou chefe de Almoxarifado. | Não. | Baixa saldo físico e consome reserva. |
| Atendimento parcial | `atendimento_parcial` | Quando ao menos um item é entregue abaixo da quantidade autorizada e há entrega maior que zero em algum item. | Auxiliar de Almoxarifado ou chefe de Almoxarifado. | Sim, por item parcial ou entregue zero. | Encerra a requisição como `atendida_parcialmente`. |
| Liberação de reserva | `liberacao_reserva` | Em cancelamento de autorizada ou atendimento parcial com quantidade não entregue. | Usuário da transição que causou a liberação. | Conforme transição principal. | Também deve existir como movimentação de estoque/reserva. |
| Devolução registrada | `devolucao_registrada` | Quando há entrada por devolução vinculada a requisição atendida ou parcialmente atendida. | Auxiliar de Almoxarifado ou chefe de Almoxarifado. | Sim, justificativa ou observação. | Não altera o status da requisição original. |
| Estorno | `estorno` | Quando o chefe de Almoxarifado estorna total ou parcialmente requisição atendida ou parcialmente atendida. | Chefe de Almoxarifado. | Sim. | Altera a requisição para `estornada` e preserva histórico original. |
| Atualização relevante por importação SCPI | `atualizacao_scpi_relevante` | Quando uma importação SCPI afeta saldo, divergência crítica ou histórico consultável relacionado a material da requisição. | Superusuário que aplicou a importação. | Não. | Deve aparecer no histórico consultável quando aplicável, sem substituir timeline operacional da requisição. |

## 5. Matriz de transições

| ID | Estado atual | Ação | Ator permitido | Pré-condições | Efeitos principais | Estoque/reserva | Novo estado | Timeline | Notificações | Critérios de aceite |
|---|---|---|---|---|---|---|---|---|---|---|
| TR-001 | Não se aplica | Criar requisição em rascunho | Solicitante para si; chefe/auxiliar de setor para funcionário do próprio setor; Almoxarifado para qualquer funcionário | Usuário ativo; beneficiário permitido; setor do beneficiário ativo; ao menos um item válido; materiais ativos, sem divergência crítica e com saldo disponível positivo; quantidade solicitada até saldo disponível no momento da criação | Cria cabeçalho, itens, criador, beneficiário e snapshot do setor do beneficiário; sem número público | Nenhuma movimentação | Rascunho | `criacao`, se a implementação registrar rascunhos; caso contrário, no primeiro envio | Nenhuma | 1.1, 11.1 a 11.5 |
| TR-002 | Rascunho | Editar rascunho | Criador ou beneficiário | Requisição em rascunho e não cancelada; itens continuam válidos | Atualiza itens e observações editáveis | Nenhuma movimentação | Rascunho | Evento opcional de atualização relevante | Nenhuma | 1.8, 1.9 |
| TR-003 | Rascunho | Descartar rascunho nunca enviado | Criador ou beneficiário | Nunca enviado para autorização; sem número público | Exclui ou descarta o rascunho sem registro operacional formal | Nenhuma movimentação | Não se aplica; registro descartado | Não obrigatório | Nenhuma | 1.9 |
| TR-004 | Rascunho | Cancelar logicamente rascunho já numerado | Criador ou beneficiário | Já foi enviado alguma vez e retornou para rascunho; possui número público, que deve ser preservado | Encerra logicamente; bloqueia edição, reenvio e atendimento | Nenhuma movimentação | Cancelada | `cancelamento` | Notifica criador e beneficiário quando aplicável | 1.9, 9.5 |
| TR-005 | Rascunho | Enviar para autorização | Criador ou beneficiário | Ao menos um item; dados válidos; se primeiro envio, gerar número público `REQ-AAAA-NNNNNN` | Define data/hora de envio; entra na fila do chefe do setor do beneficiário; bloqueia edição direta | Nenhuma movimentação | Aguardando autorização | `envio_autorizacao` ou `reenvio_autorizacao` | Notifica chefe do setor do beneficiário | 1.6, 9.1 |
| TR-006 | Aguardando autorização | Retornar para rascunho | Criador ou beneficiário | Requisição ainda não autorizada nem recusada | Remove da fila de autorização; preserva número público; permite edição em rascunho | Nenhuma movimentação | Rascunho | `retorno_rascunho` | Resolve notificação de autorização pendente; sem notificação especial obrigatória | 1.7, 1.8, 9.6 |
| TR-007 | Recusada ou Rascunho | Reenviar requisição recusada ou retornada | Criador ou beneficiário | Correções permitidas; ao menos um item válido; número público preservado se já existir | Retorna à fila de autorização; registra novo envio | Nenhuma movimentação | Aguardando autorização | `reenvio_autorizacao` | Notifica chefe do setor do beneficiário | 2.6, 9.1 |
| TR-008 | Aguardando autorização | Autorizar totalmente | Chefe do setor do beneficiário, incluindo chefe do Almoxarifado para beneficiários do setor Almoxarifado | Todos os itens com material ativo, sem divergência crítica e saldo disponível atual suficiente; quantidade autorizada igual à solicitada; lock de estoque | Persiste quantidades autorizadas; registra chefe e data/hora de autorização | Reserva automática das quantidades autorizadas; não baixa saldo físico | Autorizada | `autorizacao_total` e movimentações de reserva | Notifica criador, beneficiário e Almoxarifado | 2.1, 2.2, 2.7 a 2.10, 9.2 |
| TR-009 | Aguardando autorização | Autorizar parcialmente | Chefe do setor do beneficiário, incluindo chefe do Almoxarifado para beneficiários do setor Almoxarifado | Ao menos um item com quantidade autorizada maior que zero; cada quantidade autorizada menor que solicitada tem justificativa; quantidade autorizada até saldo disponível atual; lock de estoque | Persiste quantidades autorizadas e justificativas | Reserva apenas quantidades autorizadas maiores que zero; não baixa saldo físico | Autorizada | `autorizacao_parcial` e movimentações de reserva | Notifica criador, beneficiário e Almoxarifado | 2.3, 2.4, 2.7 a 2.10, 9.2 |
| TR-010 | Aguardando autorização | Bloquear autorização com todos os itens zerados | Chefe do setor do beneficiário | Todas as quantidades autorizadas seriam zero | Impede transição e orienta recusa da requisição inteira | Nenhuma movimentação | Aguardando autorização | Nenhum evento de transição; pode registrar tentativa bloqueada em auditoria técnica | Nenhuma | 2.5 |
| TR-011 | Aguardando autorização | Recusar requisição inteira | Chefe do setor do beneficiário | Motivo obrigatório informado | Registra motivo, chefe e data/hora da recusa; sai da fila | Nenhuma movimentação | Recusada | `recusa` | Notifica criador e beneficiário | 2.6, 9.3 |
| TR-012 | Aguardando autorização | Bloquear autorização por divergência crítica | Chefe do setor do beneficiário | Algum material possui divergência crítica ativa | Impede autorização do item/requisição até resolução da divergência | Nenhuma movimentação | Aguardando autorização | Nenhum evento de transição; pode registrar tentativa bloqueada em auditoria técnica | Nenhuma | 2.11, 7.3, 8.8 |
| TR-013 | Aguardando autorização | Bloquear autorização acima do saldo disponível atual | Chefe do setor do beneficiário | Quantidade autorizada pretendida excede saldo disponível recalculado no momento da confirmação | Impede reserva acima do saldo; exige reduzir autorização ou recusar | Nenhuma movimentação | Aguardando autorização | Nenhum evento de transição; pode registrar tentativa bloqueada em auditoria técnica | Nenhuma | 2.8, 2.9, 2.10 |
| TR-014 | Aguardando autorização | Cancelar enquanto aguarda autorização | Criador ou beneficiário | Requisição aguardando autorização | Remove da fila; encerra requisição; não exige justificativa | Nenhuma movimentação | Cancelada | `cancelamento` | Notifica criador e beneficiário; resolve notificação de autorização pendente | 1.10, 9.5, 9.6 |
| TR-015 | Autorizada | Cancelar requisição autorizada | Criador, beneficiário, auxiliar de Almoxarifado ou chefe de Almoxarifado | Justificativa obrigatória; requisição ainda sem atendimento | Encerra requisição; registra motivo de cancelamento | Libera reservas; não altera saldo físico | Cancelada | `cancelamento` e `liberacao_reserva` | Notifica criador e beneficiário | 1.11, 9.5 |
| TR-016 | Atendida parcialmente, Atendida ou Estornada | Bloquear cancelamento após atendimento ou estorno | Qualquer usuário | Estado encerrado operacionalmente | Impede cancelamento; quando aplicável, orientar estorno | Nenhuma movimentação | Estado atual preservado | Nenhum evento de transição; pode registrar tentativa bloqueada em auditoria técnica | Nenhuma | 1.12, 6.3 |
| TR-017 | Autorizada | Atender totalmente | Auxiliar de Almoxarifado ou chefe de Almoxarifado | Todos os itens autorizados entregues conforme quantidade autorizada; saldo físico suficiente; retirada registrada | Registra data/hora, responsável, pessoa que retirou se diferente e observação opcional | Baixa saldo físico pela quantidade entregue e consome reserva correspondente | Atendida | `atendimento_total` | Notifica criador e beneficiário | 3.2, 3.9, 9.4 |
| TR-018 | Autorizada | Atender parcialmente | Auxiliar de Almoxarifado ou chefe de Almoxarifado | Ao menos um item entregue com quantidade maior que zero; qualquer entrega menor que autorizada tem justificativa; saldo físico suficiente para o entregue | Registra atendimento parcial; encerra a requisição sem pendência automática | Baixa apenas entregue; consome reserva entregue; libera reserva não entregue | Atendida parcialmente | `atendimento_parcial` e `liberacao_reserva` | Notifica criador e beneficiário | 3.3, 3.7, 9.4 |
| TR-019 | Autorizada | Atendimento com item entregue zero | Auxiliar de Almoxarifado ou chefe de Almoxarifado | Item específico autorizado com quantidade maior que zero; justificativa obrigatória; ao menos outro item deve ter entrega maior que zero para finalizar atendimento | Persiste quantidade entregue zero e justificativa no item | Não baixa saldo físico do item zerado; libera reserva correspondente | Atendida parcialmente, se houver entrega em outro item | `atendimento_parcial` e `liberacao_reserva` | Notifica criador e beneficiário | 3.4 |
| TR-020 | Autorizada | Bloquear atendimento com todos os itens entregues em zero | Auxiliar de Almoxarifado ou chefe de Almoxarifado | Nenhum item teria quantidade entregue maior que zero | Impede finalização como atendida ou atendida parcialmente; orienta cancelamento da autorizada com justificativa | Nenhuma movimentação de baixa; reservas permanecem até cancelamento | Autorizada | Nenhum evento de transição; pode registrar tentativa bloqueada em auditoria técnica | Nenhuma | 3.6 |
| TR-021 | Autorizada | Cancelar autorizada sem saldo físico para atender nenhum item | Auxiliar de Almoxarifado ou chefe de Almoxarifado, também criador ou beneficiário se optar por cancelar | Nenhum item possui saldo físico suficiente para entrega; justificativa obrigatória por ser autorizada | Encerra requisição como cancelada | Libera todas as reservas; não baixa saldo físico | Cancelada | `cancelamento` e `liberacao_reserva` | Notifica criador e beneficiário | 3.8, 1.11, 9.5 |
| TR-022 | Atendida ou Atendida parcialmente | Registrar devolução vinculada | Auxiliar de Almoxarifado ou chefe de Almoxarifado | Requisição atendida ou parcialmente atendida; quantidade devolvida não ultrapassa quantidade entregue líquida de devoluções anteriores; justificativa ou observação obrigatória | Registra devolução vinculada à requisição e ao item | Aumenta saldo físico; não altera reserva; não altera status da requisição original | Estado atual preservado | `devolucao_registrada` | Não há notificação obrigatória definida | 4.1 a 4.4 |
| TR-023 | Atendida ou Atendida parcialmente | Estornar requisição | Chefe de Almoxarifado | Justificativa obrigatória; preservar operação original; quantidade estornada válida | Registra estorno total ou parcial; encerra definitivamente a requisição como estornada | Devolve saldo físico conforme quantidade estornada; registra movimentação inversa | Estornada | `estorno` | Não há notificação obrigatória definida | 6.1, 6.2 |
| TR-024 | Estornada | Bloquear ações após estorno | Qualquer usuário | Requisição estornada | Impede corrigir, reenviar, atender ou cancelar; permite apenas consulta ao histórico e timeline | Nenhuma movimentação | Estornada | Nenhum evento de transição | Nenhuma | 6.3 |

## 6. Regras especiais por quantidade

- **Quantidade solicitada:** quantidade informada no item durante a criação ou edição permitida do rascunho. Deve respeitar o saldo disponível no momento da criação, mas esse saldo é recalculado na autorização.
- **Quantidade autorizada:** quantidade aprovada pelo chefe do setor do beneficiário. Deve ser persistida separadamente da quantidade solicitada.
- **Quantidade entregue:** quantidade efetivamente retirada no atendimento pelo Almoxarifado. Deve ser persistida separadamente da quantidade solicitada e autorizada.
- **Quantidade autorizada <= quantidade solicitada:** o sistema nunca deve permitir autorização acima do solicitado.
- **Quantidade entregue <= quantidade autorizada:** o sistema nunca deve permitir entrega acima do autorizado.
- **Justificativa de autorização parcial:** obrigatória para cada item cuja quantidade autorizada seja menor que a solicitada, incluindo item autorizado com zero.
- **Justificativa de atendimento parcial:** obrigatória para cada item cuja quantidade entregue seja menor que a autorizada, incluindo item entregue com zero.
- **Item autorizado com zero:** permitido somente com justificativa e desde que a requisição tenha ao menos um item com quantidade autorizada maior que zero; item zerado não gera reserva.
- **Item entregue com zero:** permitido somente com justificativa para aquele item e desde que a requisição tenha ao menos um item com quantidade entregue maior que zero; item zerado não baixa saldo físico e libera a reserva correspondente.
- **Atendimento parcial versus requisição pendente:** atendimento parcial encerra automaticamente a requisição. A quantidade não entregue não permanece pendente na mesma requisição; se houver necessidade futura, o usuário deve seguir novo fluxo permitido, como nova requisição ou cópia quando aplicável.
- **Referência do status final:** se a quantidade autorizada foi menor que a solicitada, mas toda a quantidade autorizada foi entregue, a requisição é `atendida`, não `atendida_parcialmente`.

## 7. Regras especiais de estoque e reserva

- A autorização cria reserva para cada item com quantidade autorizada maior que zero.
- A autorização não baixa saldo físico.
- O atendimento consome a reserva correspondente e baixa saldo físico somente pela quantidade efetivamente entregue.
- O atendimento parcial consome a reserva da quantidade entregue e libera a reserva da quantidade autorizada não entregue.
- O cancelamento de requisição autorizada libera a reserva e não altera saldo físico.
- O estorno devolve saldo físico conforme regras da operação estornada e preserva o histórico original.
- A devolução vinculada a requisição atendida ou parcialmente atendida aumenta saldo físico, não altera o status da requisição original e não recria reserva.
- Divergência crítica ocorre quando saldo físico fica menor que saldo reservado; materiais nessa situação ficam bloqueados para novas requisições e novas autorizações até resolução.
- Operações críticas de autorização, cancelamento de autorizada, atendimento, devolução e estorno exigem transação atômica e lock nas linhas de estoque afetadas.
- O saldo disponível deve ser calculado como `saldo físico - saldo reservado`; não deve ser usado como campo manual de decisão sem recálculo no momento crítico.

## 8. Ações bloqueadas por estado

| Estado | Ações bloqueadas | Motivo |
|---|---|---|
| Rascunho | Autorizar, atender, registrar devolução, estornar, baixar estoque | Ainda não é requisição autorizável/atendível; sem reserva e sem baixa. |
| Aguardando autorização | Editar itens diretamente, atender, registrar devolução, estornar, cancelar como autorizada | Deve retornar para rascunho antes de editar; ainda não há autorização nem reserva. |
| Recusada | Autorizar sem reenvio, atender, registrar devolução, estornar, cancelar como autorizada | Requisição foi recusada e só pode seguir por correção e reenvio permitido. |
| Autorizada | Editar itens, reenviar, autorizar novamente, registrar devolução, estornar antes de atendimento | Já possui decisão de autorização e reserva; deve seguir para atendimento ou cancelamento permitido. |
| Atendida parcialmente | Editar, reenviar, autorizar novamente, atender novamente, cancelar | Estado final operacional; correção deve ocorrer por devolução ou estorno, conforme caso. |
| Atendida / finalizada | Editar, reenviar, autorizar novamente, atender novamente, cancelar | Estado final operacional; correção deve ocorrer por devolução ou estorno, conforme caso. |
| Cancelada | Editar, reenviar, autorizar, atender, registrar devolução, estornar | Requisição encerrada antes da retirada final; não há saída de estoque a estornar. |
| Estornada | Corrigir, reenviar, autorizar, atender, cancelar, registrar nova devolução operacional | Estorno encerra definitivamente a requisição; somente consulta ao histórico e timeline deve permanecer. |

## 9. Recomendações de implementação futura

- Criar enum de estados com os nomes técnicos canônicos deste documento.
- Criar enum de eventos de timeline com os nomes técnicos canônicos deste documento.
- Criar tabela declarativa de transições contendo estado atual, ação, atores/policies exigidas, pré-condições, efeitos e estado resultante.
- Implementar função única aplicadora de transição para validar estado atual, policy, pré-condições, efeitos de estoque, timeline e estado final.
- Centralizar policies em `policies.py` ou equivalente, reutilizadas por views e services.
- Services devem ser a única camada que altera status, quantidades autorizadas/entregues, reservas e estoque.
- Timeline deve ser gravada junto da transição principal, dentro da mesma operação de domínio.
- Notificações devem ser publicadas após commit, por mecanismo de eventos, sem interferir no sucesso da operação principal.
- Testes de transição devem cobrir caminho feliz, permissão negada, transição inválida, conflito de domínio, erro de saldo e concorrência em PostgreSQL quando houver estoque/reserva.
- Contratos DRF de ações de domínio devem declarar entrada, saída, status HTTP, envelope de erro, permissões e schema OpenAPI conforme `docs/design-acesso-rapido/api-contracts.md`.

## 10. Pontos a confirmar

- A documentação registra que o detalhe da requisição deve incluir criação na timeline, mas o backlog do piloto diz que rascunhos nunca enviados não precisam gerar timeline operacional formal e que ela pode começar no primeiro envio. A implementação deve decidir se haverá evento técnico de criação de rascunho ou apenas evento formal no primeiro envio.
- Não há notificação obrigatória explicitamente definida para devolução registrada ou estorno de requisição. Até decisão posterior, esses eventos devem aparecer na timeline e nas movimentações, sem assumir notificação obrigatória.

