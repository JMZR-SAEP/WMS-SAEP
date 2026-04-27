# 2. Modelo de Domínio e Regras de Negócio

## 2.1 Entidades principais

### Usuário / Funcionário

Representa uma pessoa com acesso ao ERP-SAEP.

Campos iniciais:

- **Nome completo**
- **Matrícula funcional**
- **E-mail**, se disponível ou necessário para contato institucional
- **Senha de acesso**
- **Status ativo/inativo**
- **Setor principal**
- **Perfis/papéis no sistema**
- **Data de criação**
- **Último acesso**, se disponível tecnicamente

Regras iniciais:

- O login deve ser feito pela matrícula funcional.
- O CPF não deve ser mantido como campo cadastral do usuário no ERP-SAEP.
- O telefone não deve ser mantido como campo cadastral do usuário no ERP-SAEP.
- A senha inicial pode ser definida a partir do CPF, mas o CPF deve ser usado apenas no momento de criação/importação da credencial inicial, sem ser armazenado como dado cadastral permanente.
- Cada usuário pertence a um único setor.
- O ERP-SAEP não terá vínculos auxiliares entre usuários e outros setores no MVP.
- O perfil de auxiliar de setor existe apenas dentro do próprio setor do usuário.
- Um auxiliar de setor pode criar requisições em nome de funcionários do seu próprio setor.
- Um auxiliar de setor não pode atuar em setores diferentes do seu.

### Setor

Representa uma unidade organizacional do SAEP.

Campos iniciais:

- **Nome**
- **Status ativo/inativo**
- **Chefe responsável**

Regras iniciais:

- Todo setor deve ter obrigatoriamente um chefe responsável.
- Um setor não pode ficar temporariamente sem chefe.
- Um chefe de setor só pode ser responsável por um setor.
- Um setor pode possuir vários funcionários.
- Requisições devem ser vinculadas ao setor principal do beneficiário.
- Setores inativos devem continuar aparecendo em históricos e relatórios de registros antigos.
- Setores inativos não devem receber novas requisições.

### Requisição

Representa o pedido de materiais feito por um usuário, para si mesmo ou em nome de outro beneficiário.

A requisição é composta por duas partes:

1. **Cabeçalho da requisição**
2. **Itens da requisição**

Campos iniciais do cabeçalho:

- **Número da requisição** no padrão `REQ-AAAA-NNNNNN`, com sequencial anual. Exemplo: `REQ-2026-000001`. Rascunhos nunca enviados ainda não possuem número público.
- **Criador**
- **Beneficiário**
- **Setor do beneficiário**
- **Status**
- **Data de criação**
- **Data de envio para autorização**
- **Data de autorização ou recusa**
- **Chefe que autorizou ou recusou**
- **Motivo da recusa**, obrigatório quando houver recusa
- **Data da retirada/finalização**
- **Auxiliar ou chefe de almoxarifado que registrou a retirada**
- **Pessoa que retirou fisicamente o material**, campo de texto livre opcional, preenchido apenas quando for diferente do beneficiário
- **Motivo de cancelamento**, obrigatório apenas quando a requisição já autorizada for cancelada
- **Observação geral da requisição** opcional

Regras iniciais:

- O detalhe da requisição deve expor uma linha do tempo com os principais eventos do ciclo de vida, ao menos em nível de domínio/API nesta fase.
- A linha do tempo deve incluir, quando aplicável: criação, envio para autorização, retorno para rascunho, reenvio, recusa, autorização total ou parcial, cancelamento, atendimento total ou parcial, devolução registrada e estorno.
- Cada evento da linha do tempo deve mostrar data/hora, usuário responsável, ação realizada e justificativa/observação quando houver.
- A linha do tempo é parte central da rastreabilidade da requisição e deve ajudar o usuário a entender o andamento do pedido.
- Todos os usuários que têm permissão para visualizar a requisição devem ver a linha do tempo completa.
- Como o ERP-SAEP representa um processo público e rastreável, eventos do fluxo operacional da requisição não devem ser escondidos dos usuários autorizados a visualizar aquela requisição.
- Uma requisição pode ser visualizada pelo criador, pelo beneficiário, pelo chefe do setor do beneficiário, por auxiliares de almoxarifado, pelo chefe de Almoxarifado e pelo superusuário para suporte técnico/administração.
- Uma requisição pode ser copiada para gerar um novo rascunho, facilitando pedidos recorrentes.
- Ao copiar uma requisição antiga, o sistema deve recalcular o saldo disponível atual de cada material.
- A cópia deve trazer apenas as quantidades originalmente solicitadas.
- A nova requisição começa do zero como rascunho, sem quantidade autorizada e sem quantidade entregue.
- Itens sem saldo disponível suficiente ou bloqueados por divergência crítica não devem ser copiados automaticamente; devem aparecer como aviso para o usuário.
- A cópia deve gerar uma nova requisição em rascunho, sem número público até o primeiro envio para autorização, com novo criador e nova data de criação.
- Ao copiar uma requisição, o sistema deve tentar manter o beneficiário original.
- O beneficiário original só pode ser mantido se o usuário que está copiando tiver permissão para criar requisição em nome desse beneficiário.
- Se o usuário não tiver permissão para criar requisição em nome do beneficiário original, o sistema deve exibir alerta e impedir a cópia com esse beneficiário, ou exigir que o beneficiário seja alterado para um permitido pelas regras de permissão.
- O usuário pode copiar apenas requisições que ele tem permissão de visualizar.
- A nova requisição só pode ser criada se o usuário também tiver permissão para criar requisição para o beneficiário resultante.
- No MVP, só é permitido copiar requisições finalizadas ou atendidas parcialmente.
- Uma requisição deve ter um ou mais itens.
- Não é permitido criar ou salvar rascunho sem itens.
- Para enviar a requisição para autorização, ela deve ter pelo menos um item.
- O número público da requisição deve ser gerado apenas no primeiro envio para autorização.
- O número da requisição deve seguir o padrão `REQ-AAAA-NNNNNN`, com sequência reiniciada a cada ano.
- Rascunhos nunca enviados para autorização não consomem número público.
- Quando uma requisição numerada retornar para rascunho, ela deve preservar o mesmo número em reenvios, cancelamentos e consultas históricas.
- Cada item representa um material solicitado.
- O status geral da requisição deve ser derivado do estado dos seus itens e das ações do fluxo.
- A requisição deve preservar quem criou, quem é o beneficiário e qual é o setor do beneficiário.

### Busca de materiais para requisição

Ao criar uma requisição, o usuário deve conseguir buscar materiais por:

- Código completo.
- Nome do material.
- Descrição.
- Grupo.
- Subgrupo.

A lista de resultados deve mostrar:

- Código completo.
- Nome.
- Unidade de medida.
- Saldo disponível.
- Observações internas, se houver.
- Indicador de divergência crítica, se houver.

Regras iniciais:

- Materiais inativos não aparecem na busca para nova requisição.
- Materiais com divergência crítica podem aparecer na busca para consulta, mas devem ficar bloqueados para seleção em nova requisição e para novas autorizações até que a divergência seja resolvida.
- Materiais sem saldo disponível podem aparecer na busca para consulta, mas devem ficar bloqueados para seleção em nova requisição.
- O usuário não pode solicitar material com saldo disponível igual ou menor que zero.
- Na criação da requisição, o usuário não pode solicitar quantidade maior que o saldo disponível no momento da criação.
- O saldo disponível validado na criação é apenas uma validação inicial.
- No momento da autorização, o sistema deve recalcular o saldo disponível antes de reservar.
- Se o saldo disponível no momento da autorização for menor que a quantidade solicitada, o chefe pode autorizar apenas até o saldo disponível ou recusar.
- A justificativa de autorização parcial continua obrigatória quando a quantidade autorizada for menor que a solicitada.

### Item da Requisição

Representa um material solicitado dentro de uma requisição.

Campos iniciais:

- **Requisição**
- **Material**
- **Unidade de medida do material**
- **Quantidade solicitada**
- **Quantidade autorizada**
- **Justificativa da autorização parcial**, quando a quantidade autorizada for menor que a solicitada
- **Quantidade entregue**
- **Justificativa do atendimento parcial**, quando a quantidade entregue for menor que a autorizada
- **Status do item**, se necessário
- **Observação do item**, se necessário

Regras iniciais:

- Cada item deve guardar separadamente quantidade solicitada, quantidade autorizada e quantidade entregue.
- A quantidade autorizada nunca pode ser maior do que a quantidade solicitada.
- A quantidade autorizada pode ser zero para um item específico, desde que o chefe informe justificativa obrigatória.
- Uma requisição autorizada deve possuir pelo menos um item com quantidade autorizada maior que zero. Caso contrário, deve ser recusada.
- A quantidade entregue nunca pode ser maior do que a quantidade autorizada.
- Quando a quantidade autorizada for menor do que a solicitada, a justificativa da autorização parcial é obrigatória.
- Quando a quantidade entregue for menor do que a autorizada, a justificativa do atendimento parcial é obrigatória.
- A quantidade entregue pode ser zero para um item específico, desde que o Almoxarifado informe justificativa obrigatória.
- Uma requisição atendida ou atendida parcialmente deve possuir pelo menos um item com quantidade entregue maior que zero. Caso contrário, deve ser cancelada com justificativa.
- Se todos os itens forem entregues conforme a quantidade autorizada, a requisição é considerada atendida/finalizada.
- Se pelo menos um item for entregue abaixo da quantidade autorizada, a requisição é considerada atendida parcialmente.

### Grupo de Material

Representa a classificação principal do material conforme estrutura do SCPI.

Campos iniciais:

- **Código do grupo**
- **Nome do grupo**

Regras iniciais:

- Grupo de material vem do SCPI via importação CSV.
- Grupo não possui status ativo/inativo próprio no ERP-SAEP.
- Se um grupo não vier mais no CSV, não deve ser inativado automaticamente; a ausência deve aparecer apenas como divergência quando aplicável.
- Regras de inativação não se aplicam diretamente a grupos.

### Subgrupo de Material

Representa a classificação secundária do material conforme estrutura do SCPI.

Campos iniciais:

- **Código do subgrupo**
- **Nome do subgrupo**
- **Grupo pai**

Regras iniciais:

- Subgrupo de material vem do SCPI via importação CSV.
- Subgrupo deve estar vinculado a um grupo pai.
- Subgrupo não possui status ativo/inativo próprio no ERP-SAEP.
- Se um subgrupo não vier mais no CSV, não deve ser inativado automaticamente; a ausência deve aparecer apenas como divergência quando aplicável.
- Regras de inativação não se aplicam diretamente a subgrupos.

### Material

Representa um item controlado pelo Almoxarifado.

Tela de detalhe do material:

- Código completo.
- Nome.
- Descrição.
- Grupo.
- Subgrupo.
- Sequencial do produto.
- Unidade de medida.
- Status ativo/inativo.
- Saldo físico.
- Saldo reservado.
- Saldo disponível.
- Indicador de divergência crítica, quando houver.
- Histórico de movimentações do material.
- Histórico de atualizações via SCPI.
- Botão para inativar, quando o usuário tiver permissão e as regras de saldo permitirem.
- Observações internas do ERP-SAEP.

Regras para observações internas:

- As observações internas são o único campo textual editável localmente no ERP-SAEP para o material.
- Elas servem para comentários operacionais internos do Almoxarifado e não alteram o cadastro oficial vindo do SCPI.
- Podem ser editadas por auxiliares de almoxarifado e chefe de almoxarifado.
- A edição das observações internas não precisa entrar no histórico/auditoria formal.
- As observações internas ficam visíveis para todos os usuários.

Campos iniciais:

- **Nome**
- **Descrição**
- **Código completo** no padrão `xxx.yyy.zzz`
  - Exemplo: `013.024.344`
  - `013` = grupo, por exemplo Material Hidráulico
  - `024` = subgrupo, por exemplo Tubos e Conexões
  - `344` = sequencial do produto, por exemplo Tubo PVC PBA JEI 4"
- **Grupo** (`xxx`)
- **Subgrupo** (`yyy`)
- **Sequencial do produto** (`zzz`)
- **Unidade de medida** proveniente do SCPI, importada via CSV e não editável no ERP-SAEP
- **Ativo/inativo**
- **Observações**
- **Histórico de auditoria**

Regras de inativação:

- Um material só pode ser inativado quando saldo físico e saldo reservado estiverem zerados.
- Materiais inativos permanecem disponíveis para consulta histórica, mas não podem ser usados em novas requisições ou novas entradas de estoque.
- A inativação pode ser feita pelo chefe de almoxarifado ou pelo superusuário.

Campos previstos para versões futuras:

- **Estoque mínimo**
- **Estoque máximo**
- **Localização física no almoxarifado**
- **Imagem do material**

Grupo e subgrupo devem ser cadastros próprios, mas as informações de grupo, subgrupo, sequencial do produto e código completo não serão geradas livremente pelo ERP-SAEP. Esses dados têm origem no SCPI e devem ser importados a partir de relatório CSV emitido pelo SCPI.

As regras detalhadas de importação, normalização, reimportação, atualização de saldo via `QUAN3`, divergências críticas e erros técnicos ficam documentadas em `docs/design/importacao-scpi-csv.md`.

Após importado, o ERP-SAEP não deve permitir edição direta dos dados cadastrais provenientes do SCPI, como nome, descrição, grupo, subgrupo e sequencial do produto. Em caso de divergência, o SCPI deve ser considerado a fonte correta para dados cadastrais do material.

O ERP-SAEP não precisa armazenar um identificador interno adicional do SCPI no MVP. O código completo `xxx.yyy.zzz` é suficiente como referência cadastral.

A unidade de medida também deve vir do SCPI via CSV. No MVP, ela não será um cadastro próprio no ERP-SAEP e não poderá ser alterada pelos usuários. O sistema deve operar sempre na unidade oficial do material, sem conversão de unidades. Conversões operacionais, como requisitar em unidade um material cadastrado em caixa, ficam fora do MVP.

Observação de nomenclatura: o trecho `zzz` do código completo será chamado de **sequencial do produto**.

## 2.2 Perfis, permissões e atuação em nome de terceiros

O sistema deve diferenciar claramente três papéis em uma requisição:

- **Beneficiário:** funcionário que necessita e receberá o material.
- **Criador da requisição:** usuário que registrou a requisição no sistema.
- **Setor responsável pela autorização:** setor ao qual o beneficiário pertence.

Regras iniciais:

O piloto inicial já deve incluir o perfil de **auxiliar de setor** para criação de requisições em nome de funcionários do próprio setor. As demais permissões do papel permanecem restritas ao escopo definido abaixo.

Papéis do piloto e do MVP:

1. **Solicitante**
   - Todo usuário é solicitante por padrão.
   - Pode criar requisições para si mesmo.

2. **Auxiliar de setor**
   - Pode criar requisições em nome de funcionários do próprio setor.
   - Não pode criar requisições em nome de funcionários de outros setores.
   - Não autoriza requisições e não opera estoque.

3. **Chefe de setor**
   - Pode criar requisições em nome de funcionários do próprio setor.
   - Pode autorizar ou recusar requisições do próprio setor.
   - Pode ver todas as requisições do setor sob sua responsabilidade.

4. **Auxiliar de Almoxarifado**
   - Pode criar requisições em nome de qualquer pessoa.
   - Pode registrar retirada.
   - Pode registrar devoluções de material vinculadas a requisições, quando aplicável.

5. **Chefe de Almoxarifado**
   - Herda as permissões operacionais de auxiliar de Almoxarifado.
   - Atua como chefe do setor de Almoxarifado.
   - Pode autorizar requisições cujo beneficiário pertence ao setor de Almoxarifado.
   - Pode registrar saídas excepcionais.
   - Pode estornar requisições finalizadas.
   - Pode cancelar requisições autorizadas com justificativa.

6. **Superusuário**
   - Atua na administração técnica do sistema.
   - Pode importar materiais via CSV.
   - Pode gerenciar usuários, setores, perfis e configurações.

Demais regras:

- Todo funcionário pode criar requisições para si mesmo.
- Chefes de setor e auxiliares de setor podem criar requisições em nome de funcionários do próprio setor.
- Chefe de almoxarifado e auxiliar de almoxarifado podem criar requisições em nome de funcionários de qualquer setor.
- O chefe de almoxarifado herda todas as permissões operacionais do auxiliar de almoxarifado.
- A autorização sempre pertence ao chefe do setor do beneficiário.
- Cada chefe de setor é responsável por apenas um setor.
- O chefe de setor pode ver todas as requisições do setor sob sua responsabilidade.
- O chefe de setor não pode editar rascunhos criados por funcionários do setor.
- O chefe de setor não pode cancelar requisições de funcionários do setor.
- O chefe de setor não pode corrigir ou reenviar requisições recusadas de funcionários do setor; essa ação cabe ao criador da requisição ou ao beneficiário.
- O chefe do Almoxarifado também atua como chefe do setor de Almoxarifado e, portanto, pode autorizar requisições cujo beneficiário pertença ao próprio setor de Almoxarifado.
- A requisição nunca deve ser vinculada ao setor do criador quando o criador estiver agindo em nome de outra pessoa; ela deve ser vinculada ao setor do beneficiário.
- Requisições em rascunho podem ser editadas somente pelo criador ou pelo beneficiário.
- Requisições enviadas para autorização não podem ser editadas diretamente.
- Enquanto uma requisição estiver aguardando autorização, o criador ou beneficiário pode cancelar o envio e retornar a requisição para rascunho, para então editá-la.
- Rascunhos nunca enviados para autorização podem ser descartados/excluídos pelo criador ou beneficiário sem justificativa, pois ainda não são registros operacionais formais.
- Rascunhos que já foram enviados alguma vez e retornaram para rascunho mantêm o número público e só podem ser cancelados logicamente, sem justificativa.
- Enquanto aguardam autorização, requisições podem ser canceladas definitivamente pelo criador ou beneficiário sem justificativa.
- Quando autorizadas, requisições podem ser canceladas pelo criador, beneficiário, auxiliar de almoxarifado ou chefe do Almoxarifado, sempre com justificativa.
- Cancelar uma requisição autorizada libera automaticamente a reserva de estoque correspondente, sem alterar o saldo físico.
- Requisições atendidas parcialmente, atendidas/finalizadas ou estornadas não podem ser canceladas.
- Requisições recusadas podem ser corrigidas e reenviadas.
- O motivo da recusa é obrigatório.
- No MVP, a recusa é sempre da requisição inteira; não haverá recusa individual por item.

Exemplo: se o chefe ou auxiliar de almoxarifado criar uma requisição em nome de um funcionário do setor de Obras, a requisição deve ser autorizada pelo chefe de Obras, e não pelo chefe do Almoxarifado.

## 2.3 Regras de estoque e movimentações

A baixa de estoque deve ocorrer somente no momento da **retirada final** do material.

A autorização da requisição não deve baixar o estoque, mas deve **reservar automaticamente** as quantidades autorizadas quando houver saldo disponível. A separação do material não deve gerar baixa adicional; ela apenas faz parte do atendimento operacional.

Na versão inicial, o evento que efetivamente reduz o saldo físico/definitivo é o registro de retirada feito pelo auxiliar de almoxarifado ou chefe de almoxarifado.

O sistema deve diferenciar:

- **Saldo físico:** quantidade total existente no almoxarifado.
- **Saldo reservado:** quantidade já comprometida por requisições autorizadas, mas ainda não retirada.
- **Saldo disponível:** quantidade livre para novas autorizações, calculada a partir do saldo físico menos o saldo reservado.

Modelo de armazenamento recomendado:

- O saldo físico deve ser armazenado como valor controlado pelas movimentações de estoque e pela importação CSV do SCPI.
- O saldo reservado deve ser armazenado como valor controlado pelas movimentações de reserva.
- O saldo disponível não precisa ser armazenado; deve ser calculado dinamicamente como `saldo físico - saldo reservado`.
- As movimentações devem permanecer como histórico e trilha de auditoria para explicar alterações feitas dentro do ERP-SAEP.
- Divergências de saldo físico devem ser corrigidas no SCPI e refletidas no ERP-SAEP por nova importação CSV.
- O ERP-SAEP não deve permitir ajuste manual de estoque no MVP.
- No momento da autorização, o sistema deve conferir o saldo disponível dentro de uma transação segura.
- Se o saldo disponível tiver mudado entre a leitura inicial e a confirmação da autorização, o sistema deve recalcular a disponibilidade.
- Se ainda houver saldo suficiente, a autorização pode ser concluída e a reserva registrada.
- Se não houver saldo suficiente, o sistema deve informar o novo saldo disponível e exigir que o chefe autorize uma quantidade menor ou recuse o item/requisição.
- O sistema nunca deve permitir que duas autorizações reservem a mesma quantidade de estoque simultaneamente.

Quando uma requisição for autorizada, o sistema deve reservar automaticamente a quantidade autorizada, desde que exista saldo disponível. Se não houver saldo disponível suficiente para a quantidade solicitada, o chefe poderá autorizar apenas até o limite disponível, caracterizando uma autorização parcial. Quando a retirada final for registrada, a reserva correspondente deve ser consumida e o saldo físico deve ser baixado.

Regras de quantidade no atendimento:

- O Almoxarifado pode entregar quantidade menor do que a autorizada quando houver motivo operacional registrado.
- O Almoxarifado não pode entregar quantidade maior do que a quantidade autorizada.
- Quando a quantidade entregue for menor que a quantidade autorizada, a requisição deve ser marcada como **atendida parcialmente**.
- Quando a quantidade entregue for igual à quantidade autorizada, a requisição deve ser marcada como **atendida/finalizada**, mesmo que a quantidade autorizada tenha sido menor do que a quantidade originalmente solicitada.
- O atendimento parcial encerra automaticamente a requisição.
- A quantidade não entregue não permanece como pendência automática na mesma requisição.
- A baixa de estoque deve considerar somente a quantidade efetivamente entregue.
- A reserva deve reduzir o saldo disponível para novas autorizações, mas não deve reduzir o saldo físico.
- Na retirada final, a reserva deve ser consumida e o saldo físico deve ser baixado.
- No momento da retirada, o sistema deve validar o saldo físico atual.
- O Almoxarifado só pode entregar até o saldo físico disponível no momento do atendimento.
- Se o saldo físico atual for menor que a quantidade autorizada, o Almoxarifado deve registrar atendimento parcial com justificativa.
- Se não houver saldo físico suficiente para entregar nenhum item, a requisição autorizada deve ser cancelada com justificativa.
- Faltas de estoque devem gerar alerta para apoiar reposição ou futura compra.
- No MVP, os alertas previstos são estoque insuficiente para autorizar toda a quantidade solicitada e divergência crítica de material, quando o saldo físico ficar menor que o saldo reservado.
- Quando a quantidade solicitada for maior que o saldo disponível, o sistema deve evidenciar essa falta durante a autorização.
- Cada item da requisição deve preservar, quando aplicável, três quantidades distintas: quantidade solicitada, quantidade autorizada e quantidade entregue.
- O beneficiário deve conseguir visualizar quando a quantidade autorizada for menor do que a quantidade originalmente solicitada.
- O chefe deve informar justificativa obrigatória quando autorizar quantidade menor do que a solicitada.
- O Almoxarifado pode entregar quantidade menor do que a autorizada, desde que informe justificativa.
- O Almoxarifado pode entregar quantidade zero em um item autorizado, desde que informe justificativa obrigatória.
- Uma requisição atendida ou atendida parcialmente deve possuir pelo menos um item com quantidade entregue maior que zero. Se nenhum item for entregue, a requisição autorizada deve ser cancelada com justificativa, e não finalizada.
- Auxiliares de almoxarifado e chefe de almoxarifado podem ver todas as requisições de todos os setores.
- Auxiliares de almoxarifado e chefe de almoxarifado não usam estado intermediário de atendimento: uma requisição autorizada deve ser concluída diretamente como atendida, atendida parcialmente ou cancelada.
- Auxiliares de almoxarifado e chefe de almoxarifado podem cancelar uma requisição autorizada, desde que informem justificativa.
- Auxiliares de almoxarifado e chefe de almoxarifado não podem devolver uma requisição autorizada para nova análise do chefe; depois de autorizada, ela deve ser atendida, atendida parcialmente, cancelada ou posteriormente estornada por perfil autorizado.
- O chefe de almoxarifado pode cancelar qualquer requisição autorizada, desde que informe justificativa.
- Movimentações de estoque já registradas não podem ser editadas ou excluídas diretamente pelo chefe de almoxarifado; correções relacionadas a requisições finalizadas devem ocorrer por estorno, e divergências de saldo devem ser corrigidas no SCPI e refletidas por nova importação CSV.
- O status final de atendimento deve considerar a quantidade autorizada como referência. Se o beneficiário solicitou 10 unidades, o chefe autorizou 6 e o Almoxarifado entregou 6, a requisição é considerada atendida completamente. Se o Almoxarifado entregar menos do que as 6 autorizadas, a requisição é considerada atendida parcialmente.

### Estoque

Representa o saldo controlado de um material no Almoxarifado.

Regras iniciais:

- No MVP, o ERP-SAEP terá apenas um almoxarifado físico.
- Cada material terá apenas um registro geral de estoque.
- O estoque deve armazenar o saldo físico.
- O estoque deve armazenar o saldo reservado.
- O saldo disponível deve ser calculado dinamicamente como `saldo físico - saldo reservado`.
- Em situações excepcionais, após importação CSV, o saldo disponível pode ficar negativo se o saldo físico importado do SCPI for menor que o saldo reservado no ERP-SAEP. Esse caso deve ser tratado como divergência crítica.
- Materiais com divergência crítica ficam bloqueados para novas requisições e novas autorizações até a situação ser resolvida.
- A divergência crítica é considerada resolvida automaticamente quando o saldo físico volta a ser maior ou igual ao saldo reservado.
- A resolução pode ocorrer após cancelamentos de requisições autorizadas, atendimentos parciais, estornos ou nova importação CSV.
- Quando resolvida, o material volta a permitir novas requisições e autorizações, desde que tenha saldo disponível.
- O estoque deve guardar a data da última movimentação ou atualização por importação CSV.
- O usuário responsável pela última movimentação não precisa ficar duplicado no estoque; essa informação deve ser consultada nas movimentações de estoque ou no histórico da importação.
- Material inativo não pode permanecer com saldo em estoque.
- Para inativar um material, o saldo físico e o saldo reservado devem estar zerados.
- Um material com saldo físico maior que zero não pode ser inativado.
- Um material com saldo reservado maior que zero não pode ser inativado.
- Materiais inativos devem continuar aparecendo em históricos de movimentações, requisições antigas e relatórios antigos.
- Materiais inativos não devem aparecer em fluxos de nova requisição ou nova entrada de estoque.
- Materiais podem ser inativados apenas pelo chefe de almoxarifado ou pelo superusuário.

### Movimentação de Estoque

Representa qualquer evento que altere ou comprometa o estoque de um material dentro do ERP-SAEP.

Campos iniciais:

- **Material**
- **Tipo de movimentação**
- **Quantidade**
- **Unidade de medida**
- **Saldo físico anterior**, quando aplicável
- **Saldo físico posterior**, quando aplicável
- **Saldo reservado anterior**, quando aplicável
- **Saldo reservado posterior**, quando aplicável
- **Usuário responsável**
- **Data/hora**
- **Origem da movimentação**, quando aplicável
- **Justificativa ou observação**, quando aplicável

Tipos iniciais de movimentação:

1. **Reserva por autorização**
   - Criada quando uma requisição é autorizada total ou parcialmente.
   - Aumenta o saldo reservado e reduz o saldo disponível.
   - Não altera o saldo físico.

2. **Liberação de reserva por cancelamento**
   - Criada quando uma requisição autorizada é cancelada antes da retirada.
   - Reduz o saldo reservado e devolve a quantidade ao saldo disponível.
   - Não altera o saldo físico.

3. **Liberação de reserva por atendimento parcial**
   - Criada quando a quantidade entregue é menor do que a quantidade autorizada.
   - Libera a parte autorizada que não foi entregue.
   - Não altera o saldo físico além da quantidade efetivamente entregue.

4. **Entrada por saldo inicial**
   - Registra o estoque inicial na implantação ou o saldo inicial de material novo criado por importação CSV.

5. **Entrada por devolução**
   - Registra material devolvido ao Almoxarifado.
   - Deve estar vinculada a uma requisição atendida ou atendida parcialmente.
   - Aumenta automaticamente o saldo físico do material.

6. **Saída por requisição**
   - Criada no momento da retirada final.
   - Reduz o saldo físico.
   - Consome automaticamente a reserva correspondente.
   - Substitui a necessidade de um tipo separado chamado “consumo de reserva”.

7. **Saída excepcional**
   - Registra perdas, vencimentos, quebras, descartes, doações ou empréstimos a outros órgãos.

8. **Estorno**
   - Registra reversão total ou parcial de uma saída já realizada.

9. **Atualização de saldo via SCPI**
   - Registra alteração de saldo físico provocada por reimportação CSV do SCPI.
   - Deve guardar saldo anterior, saldo novo, diferença, data/hora e usuário responsável pela importação.
   - Não é ajuste manual de estoque.

Origens possíveis da movimentação:

- Requisição
- Item da requisição
- Nota fiscal
- Saída excepcional
- Estorno
- Saldo inicial
- Importação CSV

### Entradas de estoque

No MVP, o ERP-SAEP não deve registrar entrada por compra diretamente. Entradas de compra e correções de saldo físico devem ser registradas no SCPI e refletidas no ERP-SAEP por importação CSV, conforme `docs/design/importacao-scpi-csv.md`.

O ERP-SAEP deve lidar com dois tipos de entrada:

1. **Saldo inicial via CSV**
   - Usado na implantação do sistema a partir do campo `QUAN3` do relatório do SCPI.
   - Também pode ser gerado automaticamente para materiais novos criados por importação CSV.

2. **Entrada por devolução**
   - Entrada decorrente de material devolvido ao Almoxarifado.
   - Deve estar sempre vinculada a uma requisição atendida ou atendida parcialmente.
   - Pode ser registrada por auxiliares de almoxarifado e chefe de almoxarifado.
   - Pode ser parcial, desde que a quantidade devolvida não ultrapasse a quantidade efetivamente entregue.
   - O sistema deve controlar o total já devolvido por item da requisição.
   - A soma das devoluções de um item nunca pode ultrapassar a quantidade efetivamente entregue daquele item.
   - Deve exigir justificativa ou observação obrigatória.
   - Deve aumentar automaticamente o saldo físico do material no ERP-SAEP.
   - A devolução não altera o status da requisição original. A requisição continua atendida/finalizada ou atendida parcialmente, e a devolução aparece apenas no histórico e nas movimentações vinculadas.

### Saídas de estoque fora de requisição

Além das saídas normais decorrentes de requisição autorizada e retirada final, o sistema deve permitir saídas excepcionais fora de requisição.

Tipos iniciais de saída fora de requisição:

- Perda
- Vencimento
- Quebra
- Descarte
- Doação
- Empréstimo a outros órgãos

Regras iniciais de permissão:

- Saídas por perda, vencimento, quebra, descarte, doação e empréstimo a outros órgãos podem ser registradas somente pelo chefe de almoxarifado.
- Toda saída fora de requisição deve exigir justificativa textual obrigatória.
- No MVP, não é obrigatório informar documento estruturado de referência, como número de processo, ofício ou autorização administrativa.
- Para doação e empréstimo a outros órgãos, o órgão de destino deve ser informado dentro da justificativa textual.
- Empréstimo a outros órgãos deve ser tratado como saída definitiva no MVP, sem controle de devolução futura.
- Saídas registradas diretamente pelo chefe de almoxarifado efetivam a baixa de estoque imediatamente.
- Saídas excepcionais não podem ultrapassar o saldo disponível do material.
- O sistema deve impedir que uma saída excepcional reduza o saldo físico a ponto de deixá-lo menor que o saldo reservado.
- Se for necessário usar material já reservado, o chefe de almoxarifado deve antes cancelar requisições autorizadas para liberar a reserva correspondente.

### Notificação

Representa um aviso interno exibido no ERP-SAEP.

Campos iniciais:

- **Destinatário usuário**, quando a notificação for individual.
- **Destinatário por setor**, quando a notificação for direcionada a responsáveis de um setor.
- **Destinatário por perfil/grupo operacional**, quando a notificação for direcionada a um grupo, como auxiliares de almoxarifado e chefe de almoxarifado.
- **Tipo da notificação**
- **Título**
- **Mensagem curta**
- **Objeto relacionado**, quando aplicável, como requisição ou movimentação.
- **Status lida/não lida**
- **Data de criação**
- **Data de leitura**
- **Data de expiração**, quando aplicável

Regras iniciais:

- Notificações podem ser destinadas a usuários específicos ou a grupos/perfis operacionais.
- Quando uma requisição for autorizada, a notificação de requisição aguardando atendimento deve ser direcionada ao grupo formado por auxiliares de almoxarifado e chefe de almoxarifado.
- Quando uma nova requisição aguardar aprovação, a notificação deve ser direcionada somente ao chefe do setor responsável, pois é ele quem pode agir autorizando ou recusando a requisição.
- Notificações devem priorizar usuários ou grupos que possam executar alguma ação relacionada ao aviso.
- Notificações devem ficar salvas no histórico do usuário enquanto forem úteis.
- Notificações lidas podem ser apagadas pelo usuário.
- O sistema deve exibir contador de notificações não lidas.
- Notificações não lidas não devem expirar rapidamente.
- Notificações lidas podem expirar após 7 dias.
- Notificações relacionadas a uma ação que já perdeu sentido devem ser marcadas como resolvidas automaticamente. Exemplo: uma notificação de autorização pendente deve ser resolvida se a requisição for retornada para rascunho ou cancelada.
- Mesmo que uma notificação expire, o histórico real da operação deve permanecer preservado na requisição, movimentação ou auditoria correspondente.

### Superusuário

O superusuário será usado apenas pelo administrador técnico do sistema, não por usuários administrativos comuns do SAEP.

O superusuário deve atuar principalmente na administração técnica e estrutural do ERP-SAEP, não como operador comum do processo.

Ficam reservados ao superusuário:

- Importação de materiais via CSV com base no SCPI, conforme regras de `docs/design/importacao-scpi-csv.md`.
- Gestão de usuários.
- Gestão de setores.
- Definição de chefes de setor.
- Definição de auxiliares de setor.
- Definição de auxiliares de almoxarifado.
- Definição do chefe de Almoxarifado.
- Configurações globais do sistema.
- Eventuais correções administrativas de alto impacto.

Regras específicas:

- O superusuário não deve atuar como operador comum em nome de outros usuários; sua função principal é administrar cadastros e configurações.
- O superusuário não deve operar estoque no dia a dia.
- O superusuário pode executar importações CSV, administrar cadastros e alterar configurações estruturais.
- O superusuário não deve registrar retirada, devolução, saída excepcional ou estorno.
- Estornos operacionais pertencem ao chefe de almoxarifado.
- O superusuário nunca pode reabrir uma requisição encerrada.
- O superusuário nunca deve excluir registros operacionais.
- Registros operacionais relevantes não devem ser excluídos diretamente. Correções devem preservar histórico e ocorrer por operações formais, como estorno, reimportação CSV ou inativação, conforme o caso.

## 2.4 Auditoria, histórico e rastreabilidade

O sistema deve preservar o histórico das operações e impedir que registros operacionais relevantes sejam apagados.

Toda ação relevante deve registrar, quando aplicável:

- Quem executou a ação.
- Quando a ação foi executada.
- Qual operação foi realizada.
- Valor anterior.
- Valor novo.
- Justificativa, quando exigida pela regra de negócio.
- Perfil ou papel usado na ação, quando relevante.

Eventos auditados no MVP:

- Criação de requisição.
- Envio da requisição para autorização.
- Retorno da requisição para rascunho após envio.
- Recusa da requisição.
- Correção e reenvio de requisição recusada.
- Autorização total ou parcial.
- Cancelamento.
- Atendimento total ou parcial, incluindo usuário do Almoxarifado responsável, data/hora, quantidades entregues e pessoa que retirou fisicamente o material quando diferente do beneficiário.
- Estorno.
- Entrada por devolução.
- Entrada por saldo inicial via importação CSV.
- Saída fora de requisição.
- Importação de materiais e atualização de saldos via CSV, incluindo eventos de **Atualização de saldo via SCPI** com saldo anterior, saldo novo, diferença, data/hora e usuário responsável.
- Alteração de usuários, setores e perfis.

A edição de requisição em rascunho não precisa ser registrada na auditoria formal do MVP. Rascunhos nunca enviados ainda não são registros operacionais oficiais; rascunhos já enviados preservam a linha do tempo a partir do primeiro envio e não exigem auditoria detalhada de cada edição posterior.

Regras iniciais de estorno:

- Apenas o **chefe de almoxarifado** pode estornar requisições finalizadas.
- Apenas o **chefe de almoxarifado** pode estornar saídas excepcionais.
- Todo estorno deve exigir justificativa obrigatória.
- O estorno deve gerar uma movimentação inversa de estoque, devolvendo automaticamente ao estoque a quantidade estornada.
- Saídas excepcionais podem ser estornadas total ou parcialmente pelo chefe de almoxarifado, sempre com justificativa obrigatória e preservação do histórico original.
- Devoluções registradas por engano podem ser estornadas total ou parcialmente pelo chefe de almoxarifado, sempre com justificativa obrigatória.
- O estorno de devolução reduz novamente o saldo físico do material, desde que exista saldo disponível suficiente para essa redução.
- O estorno de devolução só pode ocorrer se houver saldo disponível suficiente.
- Se o material devolvido já tiver sido reservado ou consumido por outra operação, o sistema deve bloquear o estorno de devolução e orientar correção pelo SCPI/importação CSV ou por estorno de operações relacionadas, quando aplicável.
- O estorno apenas devolve saldo físico e aumenta o saldo disponível.
- O estorno não reautoriza requisições, não atende requisições e não cria pendências automaticamente.
- O sistema deve permitir estorno parcial, quando apenas parte da quantidade retirada precisar ser revertida.
- Uma requisição estornada é encerrada definitivamente e não pode ser corrigida ou atendida novamente.
- O histórico original da requisição deve permanecer preservado, incluindo quem registrou a retirada, quando ela ocorreu, quais itens foram entregues e qual foi a justificativa do estorno.
