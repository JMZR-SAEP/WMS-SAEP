# 1. Mapa de Processos do Almoxarifado

## 1.1 Objetivo

Descrever os fluxos operacionais do módulo de Almoxarifado do ERP-SAEP, incluindo criação de requisição, autorização, atendimento, cancelamento, devolução, saídas excepcionais e estornos.

## 1.2 Fluxo principal de requisição

O fluxo principal de uma requisição de material no Almoxarifado segue a lógica abaixo:

1. A requisição é criada, idealmente, pelo próprio funcionário que necessita do material, chamado aqui de **beneficiário**.
2. Como nem todos os funcionários têm familiaridade com tecnologia, alguns perfis podem criar requisições em nome de terceiros:
   - O **chefe de setor** pode criar requisições em nome de funcionários do próprio setor.
   - O **auxiliar do setor** pode criar requisições em nome de funcionários do próprio setor.
   - O **chefe de almoxarifado** pode criar requisições em nome de qualquer funcionário.
   - O **auxiliar de almoxarifado** pode criar requisições em nome de qualquer funcionário.
3. A requisição é encaminhada para autorização do **chefe do setor do beneficiário**.
4. Após autorizada, a requisição passa para atendimento pelo Almoxarifado.
5. Os funcionários do Almoxarifado separam, entregam e registram a retirada dos materiais.
6. O estoque é baixado somente no momento da **retirada final**.
7. A requisição é finalizada após o registro da retirada pelo Almoxarifado.

Não é necessária confirmação posterior do solicitante ou beneficiário para concluir a retirada. O registro feito pelo Almoxarifado é suficiente para finalizar o ciclo operacional.

## 1.3 Estados da requisição

A requisição deve possuir um ciclo de vida claro, com estados explícitos. A versão inicial dos estados é:

1. **Rascunho**
   - Requisição criada, mas ainda não enviada para autorização.
   - Toda requisição recém-criada começa como rascunho.
   - Rascunho recém-criado ainda não possui número público rastreável.
   - O número público da requisição é gerado apenas no primeiro envio para autorização.
   - Não é permitido salvar rascunho sem itens.
   - Pode ser editada pelo criador ou pelo beneficiário enquanto permanecer nesse estado.

2. **Aguardando autorização**
   - Requisição enviada para análise do chefe do setor do beneficiário.
   - No primeiro envio para autorização, o sistema gera o número público da requisição no padrão `REQ-AAAA-NNNNNN`.
   - Ainda não gera baixa de estoque.

3. **Recusada**
   - Requisição negada pelo chefe do setor do beneficiário.
   - Deve registrar motivo da recusa.

4. **Autorizada**
   - Requisição aprovada pelo chefe do setor do beneficiário.
   - Fica disponível para atendimento pelo Almoxarifado.
   - Ainda não gera baixa de estoque, mas gera reserva de estoque.

5. **Atendida parcialmente**
   - Parte das quantidades autorizadas foi entregue.
   - O estoque deve ser baixado apenas na quantidade efetivamente retirada.
   - A parte autorizada e não entregue deve ter sua reserva liberada.

6. **Atendida / finalizada**
   - Todas as quantidades autorizadas foram entregues e a retirada foi registrada pelo Almoxarifado.
   - Nesse momento ocorre a baixa definitiva do estoque.

7. **Cancelada**
   - Requisição encerrada antes da retirada final.
   - Rascunho nunca enviado para autorização pode ser descartado/excluído pelo criador ou beneficiário sem justificativa, pois ainda não virou requisição formal nem consumiu número público.
   - Rascunho que já foi enviado alguma vez e retornou de autorização mantém seu número público e só pode ser cancelado logicamente, sem justificativa.
   - Enquanto estiver aguardando autorização, o criador ou beneficiário pode cancelar definitivamente sem justificativa.
   - Quando autorizada, pode ser cancelada pelo criador, beneficiário, funcionário do Almoxarifado ou chefe do Almoxarifado, sempre com justificativa.
   - Ao cancelar uma requisição autorizada, o sistema deve liberar automaticamente as quantidades reservadas, devolvendo-as ao saldo disponível. O saldo físico não muda, pois ainda não houve retirada.
   - Requisições atendidas parcialmente, atendidas/finalizadas ou estornadas não podem ser canceladas.

8. **Estornada**
   - Retirada finalizada anteriormente foi revertida por algum motivo.
   - O estorno deve preservar o histórico original e registrar a movimentação inversa no estoque.

Esses estados formam a base do controle operacional e devem ser usados tanto nos contratos do sistema quanto nas regras de negócio.

## 1.4 Fluxos alternativos e exceções

Fluxos alternativos inicialmente previstos:

- Recusa da requisição pelo chefe do setor do beneficiário.
- Correção e reenvio de uma requisição recusada.
- Retorno de uma requisição enviada para rascunho enquanto ainda aguarda autorização.
- Cancelamento antes da retirada final.
- Atendimento parcial quando nem todos os itens ou quantidades autorizadas puderem ser entregues.
- Estorno após retirada final, preservando o histórico original.

Regras iniciais:

- Enquanto estiver em **rascunho**, a requisição pode ser editada somente por quem a criou ou pelo beneficiário.
- Depois de enviada para autorização, a requisição não pode mais ser editada diretamente.
- Enquanto estiver aguardando autorização, o criador ou beneficiário pode cancelar o envio e retornar a requisição para rascunho, para então editá-la.
- Retornar uma requisição para rascunho não exige justificativa.
- Ao retornar para rascunho, a requisição deve ser removida da fila de autorização do chefe sem necessidade de notificação especial.
- O histórico deve registrar que a requisição voltou para rascunho, preservando o registro do envio anterior.
- O número público é gerado apenas no primeiro envio para autorização.
- A requisição deve manter o mesmo número ao retornar para rascunho e ao ser reenviada.
- Rascunho nunca enviado para autorização pode ser descartado/excluído pelo criador ou beneficiário sem justificativa, pois ainda não virou requisição formal nem consumiu número público.
- Rascunho que já foi enviado alguma vez e retornou de autorização mantém seu número público e só pode ser cancelado logicamente, sem justificativa.
- Enquanto estiver aguardando autorização, o criador ou beneficiário pode retornar a requisição para rascunho sem justificativa, ou cancelar definitivamente sem justificativa.
- Quando autorizada, a requisição pode ser cancelada pelo criador, beneficiário, funcionário do Almoxarifado ou chefe do Almoxarifado, sempre com justificativa.
- Ao cancelar uma requisição autorizada, o sistema deve liberar automaticamente as quantidades reservadas, devolvendo-as ao saldo disponível. O saldo físico não muda, pois ainda não houve retirada.
- Requisições atendidas parcialmente, atendidas/finalizadas ou estornadas não podem ser canceladas; quando aplicável, devem ser tratadas por estorno.
- Quando uma requisição for recusada, o chefe deve informar obrigatoriamente o motivo da recusa.
- A observação geral da requisição é opcional.
- Justificativa de autorização parcial é obrigatória quando o chefe autorizar quantidade menor do que a solicitada.
- Justificativa de atendimento parcial é obrigatória quando o Almoxarifado entregar quantidade menor do que a autorizada.
- Motivo de cancelamento é obrigatório somente para cancelamento de requisição já autorizada.
- Motivo de estorno é obrigatório.
- Uma requisição recusada pode ser corrigida e reenviada, sem necessidade de criar uma nova requisição do zero.
- Ao ser reenviada após correção, a requisição volta para o estado **aguardando autorização**.
- O Almoxarifado pode entregar quantidade menor do que a autorizada, com justificativa.
- O atendimento parcial encerra automaticamente a requisição; o saldo não entregue não permanece pendente dentro da mesma requisição.
- O Almoxarifado não pode entregar quantidade maior do que a quantidade autorizada.
- Os alertas previstos no MVP são estoque insuficiente para autorizar toda a quantidade solicitada e divergência crítica de material, quando o saldo físico ficar menor que o saldo reservado.
- Estornos de requisições finalizadas só podem ser realizados pelo chefe de almoxarifado.
- Estornos de saídas excepcionais só podem ser realizados pelo chefe de almoxarifado.
- Todo estorno deve exigir justificativa obrigatória.
- O estorno deve devolver automaticamente ao estoque a quantidade estornada.
- O sistema deve permitir estorno parcial.
- Uma requisição estornada não pode ser corrigida e atendida novamente; o estorno encerra definitivamente aquela requisição.
- Regras detalhadas de devolução, saída excepcional e estornos operacionais ficam consolidadas em `docs/design/modelo-dominio-regras.md`.
