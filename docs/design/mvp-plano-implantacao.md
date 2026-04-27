# 3. MVP e Plano de Implantação

## 3.1 Escopo do Piloto Inicial

O piloto inicial é uma entrega controlada para validar o fluxo principal do ERP-SAEP com usuários reais, antes de liberar todas as funcionalidades do MVP completo.

O piloto inicial deve incluir:

- Materiais de consumo cotidiano, como limpeza, copa/cozinha, escritório, higiene, café, chá, açúcar, papel higiênico e itens similares.
- Participação de todos os setores como solicitantes, desde que as requisições sejam limitadas aos materiais incluídos no piloto.
- Criação de requisição.
- Autorização ou recusa pelo chefe do setor do beneficiário.
- Retirada registrada pelo Almoxarifado.
- Baixa de estoque na retirada.
- Notificações internas simples para apoiar o fluxo.
- Controle em papel mantido em paralelo durante o período de validação.

O piloto inicial não deve incluir, salvo necessidade específica durante a validação:

- Relatórios completos.
- Saídas fora de requisição.
- Estornos operacionais complexos.
- Rotinas completas de gestão do Almoxarifado.

O objetivo do piloto é validar se o fluxo de requisição, autorização e retirada funciona bem no domínio, nas regras de negócio e nas integrações técnicas do sistema.

## 3.2 Escopo do MVP Completo

O MVP completo representa a primeira versão operacional mínima do módulo de Almoxarifado, após validação do piloto inicial.

O MVP completo deve incluir importação de materiais por arquivo CSV, usando como base os dados provenientes do SCPI. As regras detalhadas dessa importação ficam documentadas em `docs/design/importacao-scpi-csv.md`.

No MVP completo, o ERP-SAEP deve tratar o SCPI como fonte oficial dos dados cadastrais dos materiais e como fonte para correções de saldo físico via importação CSV. O ERP-SAEP utilizará esses dados para operação interna do Almoxarifado, mas não substituirá o cadastro oficial mantido no SCPI.

O MVP completo deve incluir apenas as seguintes entradas de estoque no ERP-SAEP:

- Saldo inicial via importação CSV do SCPI, conforme `docs/design/importacao-scpi-csv.md`
- Entrada por devolução vinculada a requisição

Entradas por compra devem ser feitas no SCPI e refletidas no ERP-SAEP por importação CSV, conforme `docs/design/importacao-scpi-csv.md`.

O MVP completo deve incluir inicialmente os seguintes alertas operacionais:

- estoque insuficiente para autorizar toda a quantidade solicitada em uma requisição;
- divergência crítica de material, quando o saldo físico importado do SCPI ficar menor que o saldo reservado no ERP-SAEP.

Divergências críticas devem aparecer como pendência/alerta no painel de Gestão do Almoxarifado para acompanhamento pelo chefe de almoxarifado até serem resolvidas.

O MVP completo deve incluir notificações internas simples no sistema. A forma de exposição dessas notificações para usuários finais pode ser definida depois; o MVP atual não deve depender de frontend dedicado, aplicativo mobile ou notificações por e-mail.

Neste momento, o ERP-SAEP não assume entrega de aplicação web responsiva como parte do escopo ativo. O foco é consolidar backend, APIs, permissões, estoque, importação e rastreabilidade.

Notificações previstas no MVP completo:

- Chefe de setor avisado quando houver nova requisição aguardando autorização.
- Solicitante/beneficiário avisado quando a requisição for autorizada.
- Solicitante/beneficiário avisado quando a requisição for recusada.
- Solicitante/beneficiário avisado quando a requisição for cancelada.
- Solicitante/beneficiário avisado quando a requisição for atendida.
- Solicitante/beneficiário avisado quando a requisição for atendida parcialmente.
- Funcionários do Almoxarifado avisados quando houver requisição autorizada aguardando atendimento.

O MVP completo não precisa notificar o superusuário sobre importações CSV. Esses casos podem ser acompanhados por histórico técnico, endpoints administrativos ou rotinas internas de gestão.

O MVP completo deve incluir os seguintes relatórios iniciais:

1. **Estoque atual**
   - Lista materiais com código completo, nome, grupo, subgrupo, unidade de medida, saldo físico, saldo reservado, saldo disponível, situação ativo/inativo, indicador de divergência crítica, data da última atualização via SCPI e data da última movimentação no ERP-SAEP.
   - Deve permitir filtros por grupo, subgrupo, ativo/inativo, somente com saldo disponível, somente com divergência crítica e busca por código ou nome.

2. **Histórico de movimentações por material**
   - Mostra entradas, saídas, reservas, liberações de reserva, devoluções, estornos e atualizações via SCPI relacionados a um material específico.
   - Deve exibir: data/hora, tipo de movimentação, quantidade, unidade de medida, saldo físico anterior, saldo físico posterior, saldo reservado anterior, saldo reservado posterior, usuário responsável, origem e justificativa/observação quando houver.
   - A origem pode ser requisição, item da requisição, importação CSV, devolução, saída excepcional ou estorno.
   - Deve permitir filtros por período, tipo de movimentação, origem e usuário responsável.

3. **Consumo por setor**
   - Mostra o consumo de materiais por setor em determinado período.
   - Deve exibir: setor, material, grupo, subgrupo, unidade de medida, quantidade consumida, quantidade de requisições e período analisado.
   - O consumo deve considerar apenas a quantidade efetivamente entregue, não a quantidade solicitada nem a quantidade autorizada.
   - Devoluções devem abater do consumo.
   - Estornos devem abater do consumo.
   - Atendimentos parciais contam apenas a quantidade efetivamente entregue.
   - Deve permitir filtros por período, setor, grupo, subgrupo e material.

4. **Consumo por material**
   - Mostra os materiais mais consumidos em determinado período.
   - Deve exibir: material, código completo, grupo, subgrupo, unidade de medida, quantidade consumida, quantidade de setores consumidores, quantidade de requisições atendidas e período analisado.
   - O consumo deve considerar apenas a quantidade efetivamente entregue.
   - Devoluções devem abater do consumo.
   - Estornos devem abater do consumo.
   - Atendimentos parciais contam apenas a quantidade efetivamente entregue.
   - Deve permitir ordenar por maior consumo.
   - Deve permitir filtros por período, grupo, subgrupo, material e setor.

5. **Requisições por status**
   - Permite acompanhar requisições em rascunho, aguardando autorização, recusadas, autorizadas, atendidas parcialmente, atendidas/finalizadas, canceladas e estornadas.
   - Deve exibir: número da requisição quando disponível, status, criador, beneficiário, setor do beneficiário, data de criação, data de envio, data de autorização/recusa, data de atendimento/cancelamento/estorno e quantidade de itens. Rascunhos nunca enviados ainda não possuem número público.
   - Valor total não entra no MVP, pois o sistema não trabalhará com preço dos materiais.
   - Deve permitir filtros por status, período, setor, beneficiário, criador, material e chefe que autorizou/recusou.
   - Chefe de setor visualiza apenas requisições do próprio setor.
   - Funcionários do Almoxarifado e chefe de Almoxarifado visualizam requisições de todos os setores.
   - Solicitante comum não acessa esse relatório geral; visualiza apenas suas próprias requisições em “Minhas requisições”.

6. **Saídas fora de requisição**
   - Lista perdas, vencimentos, quebras, descartes, doações e empréstimos a outros órgãos.
   - Deve exibir: data/hora, tipo da saída, material, código completo, grupo, subgrupo, unidade de medida, quantidade, chefe de almoxarifado responsável, justificativa textual, status da saída, data do estorno quando houver e justificativa do estorno quando houver.
   - O tipo da saída pode ser perda, vencimento, quebra, descarte, doação ou empréstimo a outros órgãos.
   - O status da saída deve indicar se ela está ativa ou estornada.
   - Deve permitir filtros por período, tipo da saída, material, grupo, subgrupo, responsável, somente estornadas e somente não estornadas.
   - Deve ser visível para funcionários do Almoxarifado, chefe de Almoxarifado e superusuário.
   - Chefe de setor não acessa esse relatório no MVP.
   - Deve permitir exportação em CSV.

7. **Histórico de importações CSV**
   - Recurso técnico para acompanhar importações do SCPI, não sendo considerado relatório operacional principal.
   - Deve exibir: data/hora da importação, usuário que executou, arquivo importado, total de produtos lógicos lidos, materiais novos, materiais atualizados, saldos atualizados, materiais ausentes no CSV, divergências críticas, erros técnicos e status da importação.
   - O status da importação pode ser: concluída, concluída com alertas ou falhou.
   - Deve ser acessível ao superusuário.
   - Chefe de almoxarifado pode acessar apenas para consulta.

Permissões de relatórios:

- Os relatórios principais do MVP devem permitir exportação em CSV.
- Exportações em PDF e XLSX ficam para versão futura.
- Funcionários do Almoxarifado podem acessar todos os relatórios.
- Chefe de Almoxarifado pode acessar todos os relatórios.
- Chefe de setor pode acessar relatórios de consumo do próprio setor e requisições do próprio setor.
- Solicitante comum não acessa relatórios gerais; visualiza apenas suas próprias requisições.
- Superusuário pode acessar relatórios para suporte técnico/administração e o histórico de importações CSV.
- Chefe de almoxarifado pode consultar o histórico de importações CSV.

### Painéis simplificados do MVP completo

Se houver frontend no futuro, o MVP completo pode trabalhar com painéis simples baseados em filas de trabalho:

1. **Minhas requisições**
   - Visível para todos os usuários.
   - Mostra requisições criadas pelo usuário ou em que ele é beneficiário.
   - Deve permitir acompanhar rascunhos, requisições aguardando autorização, autorizadas, recusadas, canceladas, atendidas e estornadas.
   - Deve exibir: número da requisição quando disponível, beneficiário, setor do beneficiário, status, data de criação, data de envio, data de autorização/recusa, data de atendimento e quantidade de itens. Rascunhos nunca enviados devem aparecer como rascunhos sem número público.
   - Deve oferecer ações conforme o status e as permissões do usuário: editar rascunho, enviar, retornar para rascunho, cancelar, copiar e visualizar.
   - Deve permitir filtros por status, período, beneficiário, material, somente requisições em que o usuário é criador e somente requisições em que o usuário é beneficiário.

2. **Autorizações pendentes**
   - Visível para chefes de setor.
   - Mostra requisições aguardando autorização cujo beneficiário pertence ao setor sob responsabilidade daquele chefe.
   - O chefe do Almoxarifado também usa esta fila para autorizar requisições do próprio setor de Almoxarifado.
   - Deve exibir: número da requisição, beneficiário, criador, setor do beneficiário, data de envio, quantidade de itens, alerta se algum item teve saldo reduzido desde a criação e status atual.
   - Ao abrir uma requisição, o chefe deve ver por item: material, unidade de medida, quantidade solicitada, saldo disponível atual, quantidade autorizada e campo de justificativa quando autorizar menos que o solicitado.
   - Deve permitir: autorizar tudo quando houver saldo disponível, autorizar parcialmente, recusar a requisição inteira com motivo obrigatório e visualizar histórico.
   - No MVP, a recusa é sempre da requisição inteira; não haverá recusa individual por item.
   - Para reduzir quantidade de um item, o chefe deve usar autorização parcial com justificativa.
   - O chefe pode autorizar quantidade zero para um item específico, com justificativa obrigatória, permitindo que a requisição siga com os demais itens autorizados.
   - O sistema não deve permitir autorizar uma requisição com todos os itens em quantidade zero. Se nenhum item for autorizado com quantidade maior que zero, o chefe deve recusar a requisição inteira com motivo obrigatório.
   - A recusa deve exigir motivo obrigatório.

3. **Atendimento do Almoxarifado**
   - Visível para funcionários do Almoxarifado.
   - Mostra requisições autorizadas aguardando atendimento.
   - Deve exibir: número da requisição, beneficiário, setor do beneficiário, chefe que autorizou, data de autorização, quantidade de itens, status e alerta de divergência crítica se algum material estiver problemático.
   - Ao abrir uma requisição autorizada, o Almoxarifado deve ver por item: material, unidade de medida, quantidade solicitada, quantidade autorizada, quantidade entregue, saldo físico atual, saldo reservado e campo de justificativa quando entregar menos que o autorizado.
   - Ao registrar a retirada, o funcionário do Almoxarifado deve informar as quantidades entregues por item, justificativas de atendimento parcial quando houver, observação geral opcional do atendimento e o nome da pessoa que retirou fisicamente o material quando ela for diferente do beneficiário. O campo de pessoa que retirou fisicamente deve ser texto livre e opcional.
   - A observação geral do atendimento deve ser visível no histórico da requisição.
   - Deve permitir registrar atendimento completo, registrar atendimento parcial, cancelar requisição autorizada com justificativa, visualizar histórico e registrar devolução depois que a requisição estiver atendida ou atendida parcialmente.

4. **Gestão do Almoxarifado**
   - Visível para chefe de almoxarifado e superusuário, respeitando as permissões de cada papel.
   - Agrupa ações sensíveis, como saídas excepcionais, estornos, devoluções, importações CSV, histórico de importações CSV, divergências críticas de materiais e relatórios gerais.
   - O superusuário pode usar o painel para suporte técnico, consulta, importações CSV, histórico de importações e relatórios permitidos, mas não deve registrar retirada, devolução, saída excepcional ou estorno operacional.
   - Deve exibir divergências críticas como pendências/alertas de gestão para acompanhamento pelo chefe de almoxarifado até a resolução.
   - A pendência de divergência crítica deve ser resolvida automaticamente quando o saldo físico do material voltar a ser maior ou igual ao saldo reservado.

## 3.3 Fora do MVP inicial

Ficam fora do MVP inicial:

- Ajuste manual de estoque no ERP-SAEP. Divergências de saldo devem ser corrigidas no SCPI e refletidas por importação CSV.
- Conversão de unidades de medida.
- Edição manual, no ERP-SAEP, dos dados cadastrais de materiais provenientes do SCPI.
- Cadastro e uso operacional de localização física/endereço físico de prateleiras.
- Relatórios avançados, como consumo por grupo/subgrupo, requisições por funcionário/beneficiário e importações por período.
- Exportação de relatórios em PDF ou XLSX.
- Aplicativo mobile dedicado.
- Modelos ou favoritos de requisição. No MVP, a recorrência será apoiada apenas pela cópia de requisições antigas.
- Relatório específico de devoluções. No MVP, devoluções devem aparecer no histórico da requisição e no histórico de movimentações por material.

## 3.4 Estratégia de implantação gradual

A implantação deve ocorrer de forma gradual, começando por um piloto.

Etapas iniciais:

1. Importar materiais do SCPI via CSV.
2. Registrar saldo inicial a partir do `QUAN3` do relatório do SCPI.
3. Iniciar piloto com materiais de consumo cotidiano solicitados pelos setores, como materiais de limpeza, copa/cozinha, escritório, higiene, café, chá, açúcar, papel higiênico e itens similares.
4. Deixar fora do piloto materiais hidráulicos, elétricos, ferramentas, EPIs, materiais de obra e outros itens mais complexos.
5. Permitir que todos os setores participem do piloto, desde que as requisições sejam limitadas aos materiais de consumo cotidiano incluídos no escopo.
6. Manter o controle em papel em paralelo durante o piloto.
7. No piloto, testar apenas o fluxo de requisição, autorização e retirada. Devoluções, saídas excepcionais, reimportações operacionais e relatórios completos ficam fora do teste inicial do piloto.
8. Rodar o fluxo principal no ERP-SAEP: requisição, autorização, atendimento, retirada e baixa de estoque.
9. O chefe de almoxarifado deve validar se o saldo inicial e os saldos operacionais estão corretos.
10. Ajustar regras, contratos, fluxos técnicos e rotinas conforme os problemas encontrados.
11. Expandir gradualmente para outros tipos de materiais quando os critérios de sucesso forem cumpridos.

O piloto não terá prazo fixo. Ele deve continuar até que os critérios de sucesso do MVP sejam atendidos com segurança.

## 3.5 Critérios de sucesso

O MVP será considerado bem-sucedido se atender aos seguintes critérios:

1. Funcionários conseguem criar requisições sem depender de papel.
2. Chefes conseguem autorizar e recusar requisições pelo sistema.
3. O Almoxarifado consegue atender requisições e baixar estoque corretamente.
4. O saldo disponível passa a ser confiável para tomada de decisão operacional.
5. Toda saída de material fica rastreada.
6. É possível consultar consumo por setor e por material.
7. É possível justificar compras com histórico de consumo.
8. O sistema é usado no dia a dia por pelo menos alguns setores piloto.
9. Os contratos e fluxos técnicos suportam a futura construção de interfaces sem retrabalho estrutural.
