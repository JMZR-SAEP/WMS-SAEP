# Estados e Transições da Requisição — WMS-SAEP

## 1. Objetivo

Síntese operacional da máquina de estados de requisições. Use este arquivo para implementar enums, tabela declarativa de transições, services, policies, timeline, movimentações de estoque e testes.

Fontes completas: `docs/design-acesso-ocasional/processos-almoxarifado.md`, `modelo-dominio-regras.md`, `criterios-aceite.md` e `docs/design-acesso-rapido/matriz-invariantes.md`.

## 2. Princípios

- Transições devem ser declarativas e aplicadas por uma função/service única.
- Services validam domínio, estado, estoque/reserva e registram timeline.
- Policies validam ator, papel, setor, beneficiário e objeto.
- Views e services chamam a mesma policy quando houver autorização contextual.
- Mudanças de saldo/reserva exigem `transaction.atomic()`, lock pessimista e ordem determinística.
- Timeline é visível a todo usuário autorizado a visualizar a requisição.
- Notificações são side effects pós-commit; nunca decidem sucesso da transação.

## 3. Estados canônicos

| Estado | Técnico | Papel no fluxo | Itens editáveis? | Estoque/reserva | Final? |
|---|---|---|---|---|---|
| Rascunho | `rascunho` | Criação/correção antes da autorização. | Sim, só criador. | Sem reserva/baixa. | Não |
| Aguardando autorização | `aguardando_autorizacao` | Fila do chefe do setor do beneficiário. | Não; deve retornar para rascunho. | Sem reserva/baixa. | Não |
| Recusada | `recusada` | Recusa da requisição inteira com motivo. | Só no fluxo de correção pelo criador/beneficiário. | Sem reserva/baixa. | Não |
| Autorizada | `autorizada` | Disponível para atendimento pelo Almoxarifado. | Não | Reserva criada na autorização. | Não |
| Atendida parcialmente | `atendida_parcialmente` | Houve entrega maior que zero e menor que autorizada em algum item. | Não | Baixa entregue, libera não entregue. | Sim |
| Atendida | `atendida` | Todas as quantidades autorizadas foram entregues. | Não | Baixa entregue, consome reserva. | Sim |
| Cancelada | `cancelada` | Encerrada antes da retirada final. | Não | Se autorizada, libera reserva; não baixa físico. | Sim |
| Estornada | `estornada` | Saída atendida revertida formalmente. | Não | Movimentação inversa de estorno. | Sim |

## 4. Eventos de timeline

| Evento | Técnico | Quando | Responsável | Justificativa |
|---|---|---|---|---|
| Criação | `criacao` | Criação do rascunho ou formalização no primeiro envio. | Criador | Não |
| Envio | `envio_autorizacao` | Rascunho vai para autorização. | Criador | Não |
| Retorno para rascunho | `retorno_rascunho` | `aguardando_autorizacao` volta para correção. | Criador ou beneficiário | Não |
| Reenvio | `reenvio_autorizacao` | Rascunho retornado é reenviado para autorização. | Criador | Não |
| Recusa | `recusa` | Chefe recusa a requisição inteira. | Chefe do setor do beneficiário | Sim |
| Autorização total | `autorizacao_total` | Todos os itens autorizados integralmente. | Chefe do setor do beneficiário | Não |
| Autorização parcial | `autorizacao_parcial` | Algum item autorizado abaixo do solicitado ou zerado. | Chefe do setor do beneficiário | Sim, por item |
| Cancelamento | `cancelamento` | Cancelamento em estado permitido. | Conforme estado | Só se autorizada |
| Atendimento total | `atendimento_total` | Tudo que foi autorizado foi entregue. | Almoxarifado | Não |
| Atendimento parcial | `atendimento_parcial` | Entrega menor que autorizada, com ao menos um item entregue. | Almoxarifado | Sim, por item |
| Liberação de reserva | `liberacao_reserva` | Cancelamento de autorizada ou atendimento parcial. | Ator da transição | Conforme transição |
| Devolução registrada | `devolucao_registrada` | Entrada por devolução vinculada. | Almoxarifado | Sim |
| Estorno | `estorno` | Reversão total/parcial pelo chefe de Almoxarifado. | Chefe de Almoxarifado | Sim |
| Atualização SCPI relevante | `atualizacao_scpi_relevante` | Importação afeta saldo/divergência de material relacionado. | Superusuário | Não |

## 5. Matriz compacta de transições

| ID | De -> Para | Ação | Atores | Regras críticas | Efeitos | Ref. |
|---|---|---|---|---|---|---|
| TR-001 | N/A -> Rascunho | Criar requisição | Solicitante para si; chefe/auxiliar de setor no próprio setor; Almoxarifado qualquer setor | Usuário ativo; beneficiário permitido; setor ativo; ao menos um item; material ativo, sem divergência, saldo positivo; quantidade <= saldo disponível inicial | Cria cabeçalho, itens, criador, beneficiário e setor do beneficiário; sem número público | 1.1, 11 |
| TR-002 | Rascunho -> Rascunho | Editar rascunho | Criador | Itens continuam válidos | Atualiza itens/observações editáveis; sem estoque | 1.8, 1.9 |
| TR-003 | Rascunho -> descartado | Descartar rascunho nunca enviado | Criador | Nunca enviado; sem número público | Pode excluir/descartar sem timeline formal, reserva ou movimentação | 1.9 |
| TR-004 | Rascunho -> Cancelada | Cancelar rascunho já numerado | Criador | Já enviado e retornado; preserva número público | Encerra logicamente; bloqueia edição/reenvio/atendimento | 1.9, 9.5 |
| TR-005 | Rascunho -> Aguardando autorização | Enviar | Criador | Ao menos um item; gera `REQ-AAAA-NNNNNN` no primeiro envio | Registra envio; entra na fila do chefe do setor do beneficiário; a partir daqui beneficiário passa a poder visualizar a requisição | 1.6, 9.1 |
| TR-006 | Aguardando autorização -> Rascunho | Retornar para rascunho | Criador ou beneficiário | Ainda não autorizada/recusada | Remove da fila; preserva número; resolve notificação pendente; após concluir, rascunho volta a ser creator-only | 1.7, 1.8, 9.6 |
| TR-007 | Recusada/Rascunho -> Aguardando autorização | Reenviar | Criador | Correções permitidas; ao menos um item; preserva número se existir | Retorna à fila; registra reenvio | 2.6, 9.1 |
| TR-008 | Aguardando autorização -> Autorizada | Autorizar total | Chefe do setor do beneficiário; chefe Almoxarifado só para setor Almoxarifado | Itens ativos, sem divergência, saldo disponível atual suficiente; lock de estoque | Persiste autorização; cria reserva; não baixa físico; notifica criador, beneficiário e Almoxarifado | 2.1, 2.2, 2.7-2.10, 9.2 |
| TR-009 | Aguardando autorização -> Autorizada | Autorizar parcial | Chefe do setor do beneficiário; chefe Almoxarifado só para setor Almoxarifado | Ao menos um item > 0; justificativa para parcial/zero; autorizado <= disponível atual; lock | Reserva apenas autorizado > 0; não baixa físico; notifica envolvidos | 2.3, 2.4, 2.7-2.10, 9.2 |
| TR-010 | Aguardando autorização -> Aguardando autorização | Bloquear autorização inválida | Chefe do setor do beneficiário | Todos itens zerados, divergência crítica ou autorização acima do saldo atual | Não transiciona; orientar recusa, reduzir autorização ou resolver divergência | 2.5, 2.8-2.11, 7.3, 8.8 |
| TR-011 | Aguardando autorização -> Recusada | Recusar inteira | Chefe do setor do beneficiário | Motivo obrigatório; sem recusa individual por item no MVP | Registra motivo, chefe e data; sai da fila; notifica criador/beneficiário | 2.6, 9.3 |
| TR-012 | Aguardando autorização -> Cancelada | Cancelar antes da autorização | Criador ou beneficiário | Estado `aguardando_autorizacao`; sem justificativa obrigatória | Remove da fila; encerra; resolve notificação pendente | 1.10, 9.5, 9.6 |
| TR-013 | Autorizada -> Cancelada | Cancelar autorizada | Criador, beneficiário ou Almoxarifado | Justificativa obrigatória; sem atendimento | Libera reservas; não altera físico; notifica criador/beneficiário | 1.11, 3.8, 9.5 |
| TR-014 | Atendida/Atendida parcialmente/Estornada -> mesmo estado | Bloquear cancelamento | Qualquer usuário | Estado final operacional | Não transiciona; orientar estorno quando aplicável | 1.12, 6.3 |
| TR-015 | Autorizada -> Atendida | Atendimento total | Auxiliar ou chefe de Almoxarifado | Todos autorizados entregues; físico suficiente; retirada registrada | Baixa físico, consome reserva, registra responsável/retirante/observação; notifica criador/beneficiário | 3.2, 3.9, 9.4 |
| TR-016 | Autorizada -> Atendida parcialmente | Atendimento parcial | Auxiliar ou chefe de Almoxarifado | Ao menos um item entregue > 0; justificativa para entrega menor/zero; físico suficiente para entregue | Baixa entregue; consome reserva entregue; libera não entregue; encerra sem pendência | 3.3, 3.4, 3.7, 9.4 |
| TR-017 | Autorizada -> Autorizada | Bloquear atendimento sem entrega | Auxiliar ou chefe de Almoxarifado | Todos itens seriam entregues com zero | Não finaliza; orientar cancelamento com justificativa | 3.6 |
| TR-018 | Atendida/Atendida parcialmente -> mesmo estado | Registrar devolução | Auxiliar ou chefe de Almoxarifado | Vinculada a requisição atendida/parcial; quantidade <= entregue líquida; justificativa/observação | Aumenta físico; não altera status nem reserva | 4.1-4.4 |
| TR-019 | Atendida/Atendida parcialmente -> Estornada | Estornar requisição | Chefe de Almoxarifado | Justificativa; quantidade válida; preservar original | Movimentação inversa; devolve físico conforme estorno; encerra definitivamente | 6.1, 6.2 |
| TR-020 | Estornada -> Estornada | Bloquear ações pós-estorno | Qualquer usuário | Requisição estornada | Permite só consulta à timeline/histórico; bloqueia corrigir, reenviar, atender, cancelar e nova devolução operacional | 6.3 |

## 6. Regras rápidas de quantidade e estoque

- Quantidades ficam separadas: `solicitada`, `autorizada`, `entregue`.
- `autorizada <= solicitada`; `entregue <= autorizada`.
- Parcial ou zero exige justificativa no item correspondente.
- Requisição autorizada precisa de ao menos um item autorizado > 0.
- Requisição atendida/parcial precisa de ao menos um item entregue > 0.
- Item autorizado com zero não gera reserva; item entregue com zero libera reserva.
- Atendimento parcial encerra a requisição; não cria pendência automática.
- Se o autorizado foi totalmente entregue, o status é `atendida`, mesmo que solicitado > autorizado.
- Autorização reserva e não baixa físico.
- Atendimento baixa físico somente do entregue e consome/libera reserva.
- Cancelamento de autorizada libera reserva e não altera físico.
- Devolução aumenta físico e não altera status.
- Estorno preserva histórico e registra movimentação inversa.
- Saldo disponível = saldo físico - saldo reservado, sempre recalculado no ponto crítico.

## 7. Ações bloqueadas por estado

| Estado | Bloqueios principais |
|---|---|
| Rascunho | Autorizar, atender, devolver, estornar, baixar estoque. |
| Aguardando autorização | Editar itens diretamente, atender, devolver, estornar, cancelar como autorizada. |
| Recusada | Autorizar sem reenvio, atender, devolver, estornar, cancelar como autorizada. |
| Autorizada | Editar, reenviar, autorizar novamente, devolver antes de atendimento, estornar antes de atendimento. |
| Atendida parcialmente | Editar, reenviar, autorizar, atender novamente, cancelar. |
| Atendida | Editar, reenviar, autorizar, atender novamente, cancelar. |
| Cancelada | Editar, reenviar, autorizar, atender, devolver, estornar. |
| Estornada | Corrigir, reenviar, autorizar, atender, cancelar, registrar nova devolução operacional. |

## 8. Pontos a confirmar

- Timeline de criação: a documentação permite registrar evento no rascunho ou apenas no primeiro envio formal. A implementação deve escolher e registrar a decisão.
- Não há notificação obrigatória definida para devolução ou estorno; até decisão posterior, esses eventos ficam na timeline/movimentações.
