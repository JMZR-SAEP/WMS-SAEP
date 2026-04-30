# Critérios de Aceite — WMS-SAEP

## 1. Requisições

### 1.1 Criação de requisição

- Todo usuário ativo deve conseguir criar uma requisição para si mesmo.
- Chefe de setor deve conseguir criar requisição em nome de funcionário do próprio setor.
- Auxiliar de setor deve conseguir criar requisição em nome de funcionário do próprio setor.
- Funcionário do Almoxarifado deve conseguir criar requisição em nome de qualquer funcionário.
- Chefe de Almoxarifado deve conseguir criar requisição em nome de qualquer funcionário.
- A requisição deve ser criada inicialmente com status `rascunho`.
- A requisição em `rascunho` nunca enviada para autorização não deve possuir número público rastreável.
- O sistema não deve permitir criar ou salvar rascunho sem pelo menos um item.
- O sistema não deve permitir adicionar material inativo à requisição.
- O sistema não deve permitir adicionar material com saldo disponível igual ou menor que zero.
- O sistema não deve permitir adicionar material com divergência crítica ativa.
- O sistema não deve permitir solicitar quantidade maior que o saldo disponível no momento da criação.
- O sistema deve registrar criador, beneficiário e setor do beneficiário.
- O setor da requisição deve ser sempre o setor do beneficiário, não o setor do criador.

### 1.2 Setor do beneficiário

Dado que um funcionário do Almoxarifado cria uma requisição em nome de um funcionário do setor de Obras  
Quando a requisição é enviada para autorização  
Então ela deve ser encaminhada ao chefe do setor de Obras, e não ao chefe do Almoxarifado.

### 1.3 Bloqueio por saldo disponível

Dado que um material possui saldo disponível igual a zero  
Quando um usuário tentar adicionar esse material a uma nova requisição  
Então o sistema deve impedir a seleção do material e indicar que não há saldo disponível.

### 1.4 Quantidade maior que saldo disponível

Dado que um material possui saldo disponível de 6 unidades  
Quando o usuário tentar solicitar 10 unidades desse material  
Então o sistema deve impedir a inclusão da quantidade solicitada e informar o saldo disponível atual.

### 1.5 Bloqueio por divergência crítica

Dado que um material está com divergência crítica ativa  
Quando um usuário tentar adicionar esse material a uma nova requisição  
Então o sistema deve impedir a seleção do material até que a divergência seja resolvida.

### 1.6 Envio para autorização

- O sistema deve permitir enviar uma requisição em rascunho para autorização quando ela tiver pelo menos um item válido.
- Ao enviar para autorização, o status deve mudar de `rascunho` para `aguardando autorização`.
- No primeiro envio para autorização, o sistema deve gerar número público no padrão `REQ-AAAA-NNNNNN`.
- Se a requisição já possuir número público por envio anterior, o reenvio deve preservar o mesmo número.
- A data/hora de envio deve ser registrada.
- A requisição deve aparecer na fila de autorizações pendentes do chefe do setor do beneficiário.
- Após o envio, a requisição não deve poder ser editada diretamente.

### 1.7 Retorno para rascunho

Dado que uma requisição está com status `aguardando autorização`  
Quando o criador ou beneficiário optar por retornar para rascunho  
Então o sistema deve alterar o status para `rascunho`, remover a requisição da fila de autorização e manter o mesmo número público da requisição.

### 1.8 Edição bloqueada enquanto aguarda autorização

Dado que uma requisição está com status `aguardando autorização`  
Quando o criador, beneficiário ou qualquer outro usuário com acesso visualizar a requisição  
Então o sistema não deve exibir campos, botões ou ações para editar diretamente os itens da requisição.

Dado que uma requisição está com status `aguardando autorização`  
Quando o criador ou beneficiário precisar alterar os itens  
Então o sistema deve oferecer apenas a ação de retornar para rascunho antes de permitir qualquer edição.

### 1.9 Cancelamento em rascunho

- O criador ou beneficiário deve conseguir descartar/excluir uma requisição em `rascunho` que nunca foi enviada para autorização.
- O descarte/exclusão de rascunho nunca enviado não deve exigir justificativa.
- O descarte/exclusão de rascunho nunca enviado não deve consumir número público, gerar reserva nem gerar movimentação de estoque.
- O criador ou beneficiário deve conseguir cancelar logicamente, sem justificativa, uma requisição em `rascunho` que já foi enviada alguma vez e retornou para rascunho.
- Rascunho já numerado e cancelado deve manter o número público e não deve poder ser editado, reenviado ou atendido.

### 1.10 Cancelamento enquanto aguarda autorização

- O criador ou beneficiário deve conseguir cancelar definitivamente uma requisição em `aguardando autorização`.
- O cancelamento em `aguardando autorização` não deve exigir justificativa.
- Ao cancelar, a requisição deve sair da fila de autorizações pendentes.
- A requisição cancelada não deve poder ser editada, reenviada ou atendida.

### 1.11 Cancelamento de requisição autorizada

Dado que uma requisição está com status `autorizada`  
Quando criador, beneficiário, funcionário do Almoxarifado ou chefe de Almoxarifado cancelar a requisição  
Então o sistema deve exigir justificativa, alterar o status para `cancelada` e liberar automaticamente as reservas vinculadas.

### 1.12 Bloqueio de cancelamento após atendimento

Dado que uma requisição está `atendida`, `atendida parcialmente` ou `estornada`  
Quando qualquer usuário tentar cancelar a requisição  
Então o sistema não deve permitir o cancelamento.

### 1.13 Cópia de requisição

- O sistema deve permitir copiar apenas requisições `atendidas` ou `atendidas parcialmente`.
- O usuário só deve conseguir copiar requisições que ele tem permissão de visualizar.
- A cópia deve gerar uma nova requisição em `rascunho`.
- A cópia não deve gerar número público imediatamente; o número deve ser gerado apenas no primeiro envio da nova requisição para autorização.
- A cópia deve registrar novo criador e nova data de criação.
- A cópia deve trazer apenas as quantidades originalmente solicitadas.
- A nova requisição não deve copiar quantidades autorizadas nem quantidades entregues.
- O sistema deve tentar manter o beneficiário original.
- O beneficiário original só deve ser mantido se o usuário que está copiando tiver permissão para criar requisição em nome dele.
- Se o usuário não tiver permissão para criar em nome do beneficiário original, o sistema deve impedir a cópia com esse beneficiário ou exigir seleção de beneficiário permitido.
- Ao copiar, o sistema deve recalcular o saldo disponível atual dos materiais.
- Itens sem saldo suficiente ou com divergência crítica ativa não devem ser copiados automaticamente.
- O sistema deve exibir aviso sobre itens que não puderam ser copiados.

## 2. Autorizações

### 2.1 Fila de autorizações pendentes

- O chefe de setor deve visualizar apenas requisições `aguardando autorização` cujo beneficiário pertence ao seu setor.
- O chefe de Almoxarifado deve visualizar requisições `aguardando autorização` cujo beneficiário pertence ao setor de Almoxarifado.
- A fila deve exibir número da requisição, beneficiário, criador, setor, data de envio e quantidade de itens.

### 2.2 Autorização total

Dado que uma requisição está `aguardando autorização`  
E todos os itens possuem saldo disponível suficiente  
Quando o chefe autorizar todos os itens integralmente  
Então o sistema deve alterar o status da requisição para `autorizada` e reservar as quantidades autorizadas.

### 2.3 Autorização parcial

Dado que uma requisição está `aguardando autorização`  
Quando o chefe autorizar quantidade menor que a solicitada em um ou mais itens  
Então o sistema deve exigir justificativa para cada item autorizado parcialmente e reservar apenas as quantidades autorizadas.

### 2.4 Autorização com item zerado

Dado que uma requisição possui mais de um item  
Quando o chefe autorizar quantidade zero para um item específico  
Então o sistema deve exigir justificativa obrigatória e permitir que a requisição siga com os demais itens autorizados.

### 2.5 Bloqueio de autorização com todos os itens zerados

Dado que o chefe está autorizando uma requisição  
Quando todos os itens estiverem com quantidade autorizada igual a zero  
Então o sistema deve impedir a autorização e orientar o chefe a recusar a requisição inteira.

### 2.6 Recusa da requisição

- O chefe deve conseguir recusar apenas a requisição inteira.
- O sistema não deve permitir recusa individual por item no MVP.
- Ao recusar, o sistema deve exigir motivo obrigatório.
- Ao recusar, o status deve mudar para `recusada`.
- Uma requisição recusada deve poder ser corrigida e reenviada pelo criador ou beneficiário.

### 2.7 Recalcular saldo no momento da autorização

Dado que uma requisição foi criada quando havia saldo disponível suficiente  
E o saldo disponível foi reduzido antes da autorização  
Quando o responsável pela autorização abrir a requisição para análise  
Então o sistema deve exibir o saldo disponível atual de cada item.

### 2.8 Bloqueio de reserva acima do saldo disponível

Dado que o saldo disponível atual de um material é menor que a quantidade solicitada  
Quando o responsável pela autorização tentar autorizar quantidade maior que o saldo disponível  
Então o sistema deve impedir a autorização dessa quantidade e permitir apenas autorização até o saldo disponível ou recusa da requisição.

### 2.9 Concorrência na autorização

Dado que duas requisições diferentes solicitam o mesmo material  
E o saldo disponível é suficiente para apenas uma delas  
Quando dois chefes tentarem autorizar as requisições ao mesmo tempo  
Então o sistema deve garantir que apenas uma autorização consiga reservar o saldo disponível.

### 2.10 Saldo alterado durante a autorização

Dado que uma requisição está em análise para autorização  
E o saldo disponível mudou antes da confirmação da autorização  
Quando o responsável pela autorização tentar confirmar a autorização  
Então o sistema deve recalcular o saldo disponível e impedir reserva acima do saldo atual.

### 2.11 Material com divergência crítica na autorização

Dado que um item da requisição possui divergência crítica ativa  
Quando o responsável pela autorização tentar autorizar esse item  
Então o sistema deve impedir a autorização do item até que a divergência seja resolvida.

## 3. Atendimento pelo Almoxarifado

### 3.1 Fila de atendimento

- Funcionários do Almoxarifado devem visualizar requisições com status `autorizada`.
- A fila deve exibir número da requisição, beneficiário, setor do beneficiário, chefe que autorizou, data de autorização, quantidade de itens e status.
- A fila deve indicar se algum material da requisição possui divergência crítica ativa.

### 3.2 Atendimento completo

Dado que uma requisição está `autorizada`  
E todos os itens autorizados possuem saldo físico suficiente  
Quando o funcionário do Almoxarifado registrar a entrega integral dos itens autorizados  
Então o sistema deve alterar o status da requisição para `atendida`, baixar o saldo físico e consumir as reservas correspondentes.

### 3.3 Atendimento parcial

Dado que uma requisição está `autorizada`  
Quando o funcionário do Almoxarifado entregar quantidade menor que a autorizada em um ou mais itens  
Então o sistema deve exigir justificativa para cada item atendido parcialmente, baixar apenas a quantidade entregue, consumir a reserva da quantidade entregue e liberar a reserva da quantidade não entregue.

### 3.4 Atendimento com entrega zero em item autorizado

Dado que uma requisição possui um item com quantidade autorizada maior que zero  
Quando o funcionário do Almoxarifado registrar quantidade entregue igual a zero para esse item  
Então o sistema deve exigir justificativa obrigatória, não baixar saldo físico desse item e liberar a reserva correspondente à quantidade não entregue.

### 3.5 Item autorizado com quantidade zero

Dado que um item foi autorizado com quantidade igual a zero  
Quando a requisição for atendida pelo Almoxarifado  
Então esse item não deve gerar baixa de estoque, não deve possuir reserva a consumir e não deve exigir quantidade entregue.

### 3.6 Bloqueio de atendimento sem entrega

Dado que uma requisição está `autorizada`  
Quando o funcionário do Almoxarifado tentar finalizar o atendimento com todos os itens entregues em quantidade zero  
Então o sistema deve impedir a finalização como `atendida` ou `atendida parcialmente` e orientar o usuário a cancelar a requisição autorizada com justificativa.

### 3.7 Saldo físico insuficiente no atendimento

Dado que uma requisição está `autorizada`  
E o saldo físico atual de um material é menor que a quantidade autorizada  
Quando o funcionário do Almoxarifado registrar o atendimento  
Então o sistema deve permitir entregar apenas até o saldo físico disponível e exigir atendimento parcial com justificativa.

### 3.8 Sem saldo físico para atender

Dado que uma requisição está `autorizada`  
E nenhum item possui saldo físico suficiente para entrega  
Quando o funcionário do Almoxarifado tentar registrar atendimento  
Então o sistema deve impedir a finalização como `atendida` ou `atendida parcialmente` e orientar o usuário a cancelar a requisição autorizada com justificativa.

### 3.9 Registro da retirada

- Ao registrar a retirada, o sistema deve gravar automaticamente data/hora do atendimento.
- Ao registrar a retirada, o sistema deve gravar o funcionário do Almoxarifado responsável.
- O sistema deve permitir informar observação geral opcional do atendimento.
- O sistema deve permitir informar, em campo de texto livre opcional, a pessoa que retirou fisicamente o material quando ela for diferente do beneficiário.
- A observação geral do atendimento deve aparecer no histórico da requisição.

## 4. Devoluções

### 4.1 Registro de devolução

- Funcionários do Almoxarifado devem conseguir registrar devolução de material.
- A devolução deve estar sempre vinculada a uma requisição `atendida` ou `atendida parcialmente`.
- A devolução deve exigir justificativa ou observação obrigatória.
- A devolução deve aumentar automaticamente o saldo físico do material.
- A devolução não deve alterar o status da requisição original.
- A devolução deve aparecer no histórico da requisição e no histórico de movimentações do material.

### 4.2 Devolução parcial

Dado que uma requisição entregou 10 unidades de um material  
Quando o funcionário do Almoxarifado registrar devolução de 3 unidades  
Então o sistema deve aumentar o saldo físico em 3 unidades e manter a requisição com o status original.

### 4.3 Limite da devolução

Dado que uma requisição entregou 10 unidades de um material  
E já foram devolvidas 3 unidades  
Quando o funcionário do Almoxarifado tentar registrar nova devolução de 8 unidades  
Então o sistema deve impedir a devolução, pois o total devolvido ultrapassaria a quantidade efetivamente entregue.

### 4.4 Bloqueio de devolução sem requisição

Dado que o funcionário do Almoxarifado está registrando uma devolução  
Quando ele não vincular a devolução a uma requisição atendida ou atendida parcialmente  
Então o sistema deve impedir o registro da devolução.

## 5. Saídas Excepcionais

### 5.1 Registro de saída excepcional

- Apenas o chefe de almoxarifado deve conseguir registrar saída excepcional.
- O sistema deve permitir os tipos: `perda`, `vencimento`, `quebra`, `descarte`, `doação` e `empréstimo a outros órgãos`.
- Toda saída excepcional deve exigir justificativa textual obrigatória.
- No MVP, o sistema não deve exigir documento estruturado, número de processo, ofício ou autorização administrativa.
- Para `doação` e `empréstimo a outros órgãos`, o órgão de destino deve ser informado dentro da justificativa textual.
- Empréstimo a outros órgãos deve ser tratado como saída definitiva no MVP.

### 5.2 Baixa de estoque por saída excepcional

Dado que o chefe de almoxarifado registra uma saída excepcional válida  
Quando a saída é confirmada  
Então o sistema deve baixar imediatamente o saldo físico do material e registrar a movimentação correspondente.

### 5.3 Bloqueio por saldo disponível

Dado que um material possui saldo físico de 100, saldo reservado de 80 e saldo disponível de 20  
Quando o chefe de almoxarifado tentar registrar saída excepcional de 30  
Então o sistema deve impedir a saída, pois ela ultrapassa o saldo disponível e comprometeria reservas existentes.

### 5.4 Saída excepcional sem justificativa

Dado que o chefe de almoxarifado está registrando uma saída excepcional  
Quando ele tentar confirmar sem preencher justificativa textual  
Então o sistema deve impedir o registro da saída.

## 6. Estornos

### 6.1 Permissão para estorno

- Apenas o chefe de almoxarifado deve conseguir realizar estornos operacionais.
- Superusuário não deve realizar estornos operacionais.
- Todo estorno deve exigir justificativa obrigatória.
- O estorno deve preservar o histórico da operação original.

### 6.2 Estorno de requisição atendida

Dado que uma requisição está `atendida` ou `atendida parcialmente`  
Quando o chefe de almoxarifado realizar estorno total ou parcial  
Então o sistema deve devolver ao saldo físico a quantidade estornada, registrar movimentação de estorno e alterar a requisição para `estornada`.

### 6.3 Ações bloqueadas após estorno de requisição

Dado que uma requisição está `estornada`  
Quando qualquer usuário com permissão de visualização abrir a requisição  
Então o sistema não deve exibir campos, botões ou ações para corrigir, reenviar, atender ou cancelar a requisição.

Dado que uma requisição está `estornada`  
Quando qualquer usuário visualizar a requisição  
Então o sistema deve permitir apenas consulta ao histórico e à linha do tempo da requisição.

### 6.4 Estorno de saída excepcional

Dado que uma saída excepcional foi registrada  
Quando o chefe de almoxarifado realizar estorno total ou parcial dessa saída  
Então o sistema deve devolver ao saldo físico a quantidade estornada e preservar a saída original no histórico.

### 6.5 Estorno de devolução

Dado que uma devolução foi registrada por engano  
Quando o chefe de almoxarifado realizar estorno total ou parcial da devolução  
Então o sistema deve reduzir novamente o saldo físico, desde que exista saldo disponível suficiente.

### 6.6 Bloqueio de estorno de devolução sem saldo disponível

Dado que uma devolução aumentou o saldo físico  
E esse saldo já foi reservado ou consumido por outra operação  
Quando o chefe de almoxarifado tentar estornar a devolução  
Então o sistema deve bloquear o estorno se não houver saldo disponível suficiente.

## 7. Materiais e Estoque

### 7.1 Busca de materiais

- O sistema deve permitir buscar materiais por código completo, nome, descrição, grupo e subgrupo.
- A lista de resultados deve exibir código completo, nome, unidade de medida, saldo disponível, observações internas quando houver e indicador de divergência crítica quando houver.
- Materiais inativos não devem aparecer para seleção em nova requisição.
- Materiais inativos devem permanecer disponíveis em históricos e relatórios.

### 7.2 Saldos do material

- O sistema deve armazenar saldo físico.
- O sistema deve armazenar saldo reservado.
- O sistema deve calcular saldo disponível como `saldo físico - saldo reservado`.
- O sistema não deve permitir ajuste manual de estoque no MVP.

### 7.3 Bloqueio por divergência crítica

Dado que um material possui saldo físico menor que saldo reservado  
Quando o sistema recalcular a situação do material  
Então o material deve ser marcado com divergência crítica e bloqueado para novas requisições e novas autorizações.

### 7.4 Resolução automática de divergência crítica

Dado que um material está com divergência crítica ativa  
Quando o saldo físico voltar a ser maior ou igual ao saldo reservado  
Então o sistema deve remover o material da lista de pendências de divergência crítica e permitir novas requisições e autorizações, desde que exista saldo disponível.

### 7.5 Inativação de material

Dado que um material possui saldo físico igual a zero e saldo reservado igual a zero  
Quando chefe de almoxarifado ou superusuário solicitar a inativação  
Então o sistema deve permitir inativar o material.

### 7.6 Bloqueio de inativação com saldo

Dado que um material possui saldo físico maior que zero ou saldo reservado maior que zero  
Quando chefe de almoxarifado ou superusuário tentar inativar o material  
Então o sistema deve impedir a inativação.

## 8. Importação SCPI CSV

### 8.1 Normalização do arquivo

- O sistema deve aceitar arquivo CSV emitido pelo SCPI em UTF-8 com BOM e separador `;`.
- O sistema deve reconstruir produtos lógicos quando descrições vierem quebradas em múltiplas linhas físicas.
- Uma nova linha lógica de produto deve começar quando a linha iniciar com código no padrão `000.000.000;`.
- Linhas que não começam com código de produto devem ser tratadas como continuação da descrição do produto anterior.

### 8.2 Pré-visualização da importação

- O sistema deve normalizar e validar tecnicamente o arquivo antes de aplicar alterações.
- O sistema deve apresentar pré-visualização com total de produtos lógicos lidos, materiais novos, materiais atualizados, saldos atualizados, materiais ausentes no CSV, divergências críticas e erros técnicos.
- O sistema deve separar alertas/divergências de erros técnicos.
- O sistema deve permitir cancelar a importação antes da aplicação.

### 8.3 Regra tudo ou nada

Dado que a importação possui erro técnico impeditivo  
Quando o superusuário tentar aplicar a importação  
Então o sistema deve impedir a aplicação e não persistir nenhuma alteração de material, grupo, subgrupo, estoque ou movimentação.

### 8.4 Importação com alertas

Dado que a importação não possui erro técnico impeditivo  
E possui alertas, materiais ausentes no CSV, saldos atualizados ou divergências críticas  
Quando o superusuário confirmar explicitamente que está ciente dos alertas  
Então o sistema deve aplicar a importação e registrar status `concluída com alertas`.

### 8.5 Atualização de saldo via SCPI

Dado que um material existente possui saldo físico diferente do valor `QUAN3` importado  
Quando a importação for aplicada  
Então o sistema deve atualizar o saldo físico e registrar evento de atualização de saldo via SCPI com saldo anterior, saldo novo, diferença, data/hora e usuário responsável.

### 8.6 Material novo na importação

Dado que o CSV contém um material cujo código completo ainda não existe no WMS-SAEP  
Quando a importação for aplicada  
Então o sistema deve criar o material como ativo, criar grupo/subgrupo quando necessário, registrar saldo inicial com base em `QUAN3` e não tratar o material como erro.

### 8.7 Material ausente no CSV

Dado que um material existe no WMS-SAEP  
E esse material não veio no CSV importado  
Quando a importação for concluída  
Então o sistema não deve inativar o material automaticamente e deve listá-lo como material ausente no CSV para análise.

### 8.8 Divergência crítica na importação

Dado que o saldo físico importado do SCPI fica menor que o saldo reservado no WMS-SAEP  
Quando a importação for aplicada  
Então o sistema deve registrar divergência crítica, bloquear o material para novas requisições e autorizações, e exibir a pendência no painel de Gestão do Almoxarifado.

### 8.9 Histórico da importação

- Toda importação aplicada ou falha deve gerar registro no histórico de importações.
- O histórico deve registrar data/hora, usuário, arquivo importado, totais lidos, materiais novos, materiais atualizados, saldos atualizados, materiais ausentes, divergências críticas, erros técnicos e status da importação.

## 9. Notificações

### 9.1 Notificação de autorização pendente

Dado que uma requisição foi enviada para autorização  
Quando o status mudar para `aguardando autorização`  
Então o sistema deve notificar o chefe do setor do beneficiário.

### 9.2 Notificação de requisição autorizada

Dado que uma requisição foi autorizada  
Quando o status mudar para `autorizada`  
Então o sistema deve notificar o criador, o beneficiário e os funcionários do Almoxarifado.

### 9.3 Notificação de requisição recusada

Dado que uma requisição foi recusada  
Quando o status mudar para `recusada`  
Então o sistema deve notificar o criador e o beneficiário.

### 9.4 Notificação de atendimento

Dado que uma requisição foi atendida ou atendida parcialmente  
Quando o atendimento for registrado  
Então o sistema deve notificar o criador e o beneficiário.

### 9.5 Notificação de requisição cancelada

Dado que uma requisição foi cancelada  
Quando o status mudar para `cancelada`  
Então o sistema deve notificar o criador e o beneficiário.

### 9.6 Resolução automática de notificação

Dado que uma notificação está relacionada a uma ação que perdeu sentido  
Quando a requisição for cancelada, retornada para rascunho ou resolvida por outra ação  
Então o sistema deve marcar a notificação como resolvida automaticamente.

### 9.7 Expiração de notificações

- Notificações não lidas não devem expirar rapidamente.
- Notificações lidas podem expirar depois de 7 dias.
- Mesmo que a notificação expire, o histórico real deve continuar na requisição, movimentação ou auditoria.

## 10. Relatórios

### 10.1 Acesso aos relatórios

- Funcionários do Almoxarifado devem conseguir acessar todos os relatórios do MVP.
- Chefe de Almoxarifado deve conseguir acessar todos os relatórios do MVP.
- Chefe de setor deve conseguir acessar apenas relatórios de consumo e requisições do próprio setor.
- Solicitante comum não deve acessar relatórios gerais.
- Superusuário deve conseguir acessar relatórios para suporte técnico/administração.

### 10.2 Exportação CSV

Dado que um usuário possui permissão para acessar um relatório  
Quando ele solicitar exportação  
Então o sistema deve gerar arquivo CSV respeitando os filtros aplicados.

### 10.3 Relatório de estoque atual

- O relatório deve exibir código completo, nome, grupo, subgrupo, unidade de medida, saldo físico, saldo reservado, saldo disponível, status ativo/inativo, indicador de divergência crítica, data da última atualização via SCPI e data da última movimentação.
- O relatório deve permitir filtros por grupo, subgrupo, ativo/inativo, somente com saldo disponível, somente com divergência crítica e busca por código ou nome.

### 10.4 Relatório de consumo

- Consumo deve considerar apenas quantidade efetivamente entregue.
- Devoluções devem abater do consumo.
- Estornos devem abater do consumo.
- Atendimentos parciais devem considerar apenas a quantidade entregue.

## 11. Permissões

### 11.1 Solicitante comum

- Todo usuário ativo deve ter permissão de solicitante.
- Solicitante comum deve conseguir criar requisição para si mesmo.
- Solicitante comum deve visualizar suas próprias requisições como criador ou beneficiário.
- Solicitante comum não deve acessar relatórios gerais.
- Solicitante comum não deve operar estoque.

### 11.2 Auxiliar de setor

- Auxiliar de setor deve conseguir criar requisição em nome de funcionários do próprio setor.
- Auxiliar de setor não deve conseguir criar requisição em nome de funcionário de outro setor.
- Auxiliar de setor não deve autorizar requisições.
- Auxiliar de setor não deve operar estoque.

### 11.3 Chefe de setor

- Chefe de setor deve conseguir criar requisição em nome de funcionários do próprio setor.
- Chefe de setor deve conseguir autorizar ou recusar requisições do próprio setor.
- Chefe de setor deve visualizar requisições do setor sob sua responsabilidade.
- Chefe de setor não deve autorizar requisições de outros setores.
- Chefe de setor não deve operar estoque.
- Chefe de setor deve acessar apenas relatórios do próprio setor, quando aplicável.

### 11.4 Auxiliar de Almoxarifado

- Auxiliar de Almoxarifado deve conseguir criar requisição em nome de qualquer funcionário.
- Auxiliar de Almoxarifado deve visualizar requisições de todos os setores.
- Auxiliar de Almoxarifado deve conseguir registrar atendimento e devolução.
- Auxiliar de Almoxarifado não deve registrar saídas excepcionais.
- Auxiliar de Almoxarifado não deve realizar estornos operacionais.

### 11.5 Chefe de Almoxarifado

- Chefe de Almoxarifado deve herdar permissões operacionais de auxiliar de Almoxarifado.
- Chefe de Almoxarifado deve conseguir registrar saídas excepcionais.
- Chefe de Almoxarifado deve conseguir realizar estornos operacionais.
- Chefe de Almoxarifado deve conseguir inativar materiais quando as regras de saldo permitirem.
- Chefe de Almoxarifado deve conseguir consultar histórico de importações CSV.

### 11.6 Superusuário

- Superusuário deve conseguir administrar usuários, setores, perfis e configurações.
- Superusuário deve conseguir importar materiais via CSV do SCPI.
- Superusuário deve conseguir acessar relatórios para suporte técnico/administração.
- Superusuário não deve operar estoque no dia a dia.
- Superusuário não deve registrar retirada, devolução, saída excepcional ou estorno operacional.
