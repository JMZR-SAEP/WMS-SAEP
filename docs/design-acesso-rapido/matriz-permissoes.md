# Matriz de Permissões — ERP-SAEP

## 1. Objetivo

Este documento consolida papéis, escopos e permissões do ERP-SAEP. Ele serve como referência canônica para implementação de `policies.py`, services, endpoints Django REST Framework e testes automatizados.

A matriz deve orientar decisões de autorização contextual por usuário, papel, setor, objeto e fase do fluxo operacional. Ela não substitui os documentos de domínio, processos e critérios de aceite; seu objetivo é tornar as permissões mais rápidas de consultar e mais difíceis de duplicar de forma inconsistente.

## 2. Princípios de autorização

- Todo usuário ativo é solicitante por padrão.
- Autorização contextual deve ser centralizada em policy.
- Views e services devem chamar a mesma policy quando houver regra por objeto, setor ou papel.
- Services devem revalidar autorização em toda escrita.
- Permissão geral em DRF não substitui validação contextual.
- Objeto fora do escopo visível pode retornar `404 not_found`.
- Objeto visível com ação negada deve retornar `403 permission_denied`.
- Superusuário atua em suporte/administração técnica e não deve operar estoque cotidiano quando a regra de negócio assim definir.
- Regras críticas de permissão não devem ficar em serializers, admin actions, signals ou condicionais espalhados em views.
- Toda ação operacional que altera status, estoque, reserva, histórico ou auditoria deve registrar o usuário e o papel/escopo usado quando relevante.

## 3. Papéis canônicos

| Papel | Nome técnico sugerido | Descrição | Escopo | Observações |
|---|---|---|---|---|
| Solicitante | `solicitante` | Papel básico de todo usuário ativo. | Próprio usuário como criador ou beneficiário. | Cria requisição para si, visualiza suas próprias requisições e não opera estoque. |
| Auxiliar de setor | `auxiliar_setor` | Usuário que apoia a criação de requisições do seu setor. | Apenas setor principal do próprio usuário. | Não autoriza requisições, não opera estoque e não atua em outros setores. |
| Chefe de setor | `chefe_setor` | Responsável por autorizar ou recusar requisições do setor sob sua responsabilidade. | Apenas setor pelo qual é chefe. | Pode criar em nome de funcionários do próprio setor e ver requisições do setor; não opera estoque. |
| Auxiliar de Almoxarifado | `auxiliar_almoxarifado` | Papel operacional do Almoxarifado. | Todos os setores para criação, visualização e atendimento. | Registra retirada e devolução; não registra saídas excepcionais nem estornos operacionais. |
| Chefe de Almoxarifado | `chefe_almoxarifado` | Responsável operacional pelo Almoxarifado. | Todos os setores para operação de Almoxarifado; setor Almoxarifado para autorização como chefe de setor. | Herda permissões do auxiliar de Almoxarifado, registra saídas excepcionais, estornos e inativa materiais quando permitido. |
| Superusuário | `superuser` | Administração técnica e suporte estrutural do sistema. | Suporte/administração técnica. | Gerencia usuários, setores, perfis, configurações e importação SCPI; não opera estoque cotidiano. |

Conceitos de requisição que não são papéis, mas controlam escopo:

| Conceito | Definição | Efeito de autorização |
|---|---|---|
| Criador da requisição | Usuário que registrou a requisição no sistema. | Pode visualizar suas requisições; pode editar rascunho, enviar, retornar para rascunho ou cancelar nos estados permitidos. |
| Beneficiário | Funcionário que necessita e receberá o material. | Pode visualizar suas requisições; pode editar rascunho, enviar, retornar para rascunho ou cancelar nos estados permitidos. |
| Setor do beneficiário | Setor principal do beneficiário no momento da requisição. | Define o setor da requisição e a fila de autorização; nunca deve ser substituído pelo setor do criador. |
| Chefe responsável pela autorização | Chefe do setor do beneficiário. | Autoriza ou recusa a requisição enquanto ela estiver `aguardando autorização`. |

## 4. Matriz geral de permissões

Valores usados:

- **Sim**: permitido para o papel, respeitando estado e validações de domínio.
- **Não**: não permitido.
- **Apenas próprio setor**: permitido somente para usuários/objetos do setor do papel.
- **Qualquer setor**: permitido sem restrição de setor, respeitando demais regras.
- **Apenas suporte/admin**: permitido apenas como administração técnica, sem operação cotidiana.
- **Fora do MVP**: documentado como fora do MVP ou postergado.

| Ação | Solicitante | Auxiliar de setor | Chefe de setor | Auxiliar de Almoxarifado | Chefe de Almoxarifado | Superusuário | Observações |
|---|---|---|---|---|---|---|---|
| Autenticar por matrícula | Sim | Sim | Sim | Sim | Sim | Sim | Usuário inativo não deve acessar. |
| Acessar como usuário ativo | Sim | Sim | Sim | Sim | Sim | Sim | Todo acesso operacional pressupõe usuário ativo. |
| Gerenciar usuários | Não | Não | Não | Não | Não | Apenas suporte/admin | Administração técnica do superusuário. |
| Gerenciar setores | Não | Não | Não | Não | Não | Apenas suporte/admin | Inclui definição de chefe responsável. |
| Gerenciar papéis | Não | Não | Não | Não | Não | Apenas suporte/admin | Inclui auxiliares, chefes e configurações estruturais. |
| Criar requisição para si | Sim | Sim | Sim | Sim | Sim | Não | Superusuário não deve atuar como operador comum. |
| Criar requisição em nome de funcionário do próprio setor | Não | Apenas próprio setor | Apenas próprio setor | Qualquer setor | Qualquer setor | Não | A requisição pertence ao setor do beneficiário. |
| Criar requisição em nome de funcionário de outro setor | Não | Não | Não | Qualquer setor | Qualquer setor | Não | Almoxarifado pode criar para qualquer funcionário. |
| Visualizar próprias requisições como criador | Sim | Sim | Sim | Sim | Sim | Apenas suporte/admin | Superusuário visualiza para suporte/administração. |
| Visualizar próprias requisições como beneficiário | Sim | Sim | Sim | Sim | Sim | Apenas suporte/admin | Criador e beneficiário podem ser pessoas diferentes. |
| Visualizar requisições do setor | Não | Não | Apenas próprio setor | Qualquer setor | Qualquer setor | Apenas suporte/admin | Chefe vê setor sob responsabilidade; Almoxarifado vê todos. |
| Visualizar requisições de todos os setores | Não | Não | Não | Sim | Sim | Apenas suporte/admin | Para atendimento, suporte e relatórios permitidos. |
| Editar rascunho | Sim | Sim | Sim | Sim | Sim | Não | Apenas criador ou beneficiário enquanto estiver em `rascunho`. Chefe não edita rascunho de terceiros. |
| Enviar para autorização | Sim | Sim | Sim | Sim | Sim | Não | Apenas criador ou beneficiário da requisição. |
| Retornar para rascunho | Sim | Sim | Sim | Sim | Sim | Não | Apenas criador ou beneficiário enquanto `aguardando autorização`. |
| Cancelar enquanto aguarda autorização | Sim | Sim | Sim | Sim | Sim | Não | Apenas criador ou beneficiário; sem justificativa. |
| Cancelar requisição autorizada | Sim | Sim | Sim | Sim | Sim | Não | Criador, beneficiário, auxiliar de Almoxarifado ou chefe de Almoxarifado; exige justificativa. |
| Copiar requisição atendida ou parcialmente atendida | Sim | Sim | Sim | Sim | Sim | Não | Usuário precisa poder visualizar a origem e criar para o beneficiário resultante. |
| Visualizar fila de autorizações | Não | Não | Apenas próprio setor | Não | Apenas setor Almoxarifado | Não | Chefe de Almoxarifado autoriza apenas requisições cujo beneficiário pertence ao Almoxarifado. |
| Autorizar requisição | Não | Não | Apenas próprio setor | Não | Apenas setor Almoxarifado | Não | Autorização pertence ao chefe do setor do beneficiário. |
| Autorizar parcialmente | Não | Não | Apenas próprio setor | Não | Apenas setor Almoxarifado | Não | Exige justificativa por item parcial. |
| Recusar requisição | Não | Não | Apenas próprio setor | Não | Apenas setor Almoxarifado | Não | Recusa é da requisição inteira no MVP e exige motivo. |
| Autorizar requisição do próprio setor | Não | Não | Sim | Não | Sim, se setor Almoxarifado | Não | "Próprio setor" do chefe de Almoxarifado é o setor Almoxarifado. |
| Autorizar requisição de outro setor | Não | Não | Não | Não | Não | Não | Mesmo Almoxarifado não autoriza requisições de outros setores. |
| Autorizar requisição do setor Almoxarifado quando chefe de Almoxarifado | Não | Não | Não | Não | Sim | Não | Herança operacional não amplia autorização para outros setores. |
| Visualizar fila de atendimento | Não | Não | Não | Sim | Sim | Apenas suporte/admin | Fila contém requisições `autorizada`. |
| Registrar atendimento total | Não | Não | Não | Sim | Sim | Não | Baixa saldo físico e consome reserva. |
| Registrar atendimento parcial | Não | Não | Não | Sim | Sim | Não | Exige justificativa e libera reserva não entregue. |
| Informar pessoa que retirou fisicamente | Não | Não | Não | Sim | Sim | Não | Campo opcional no registro de retirada quando diferente do beneficiário. |
| Cancelar autorizada por falta operacional | Não | Não | Não | Sim | Sim | Não | Exige justificativa e libera reserva; também permitido ao criador/beneficiário quando autorizada. |
| Liberar reserva não entregue | Não | Não | Não | Sim | Sim | Não | Efeito do atendimento parcial ou cancelamento autorizado, não ação isolada livre. |
| Buscar materiais para requisição | Sim | Sim | Sim | Sim | Sim | Apenas suporte/admin | Materiais inativos, sem saldo ou com divergência crítica não podem ser selecionados para nova requisição. |
| Consultar materiais | Sim | Sim | Sim | Sim | Sim | Apenas suporte/admin | Materiais e observações internas ficam visíveis aos usuários; relatórios seguem escopo próprio. |
| Editar observações internas do material | Não | Não | Não | Sim | Sim | Não | Único campo textual editável localmente no material. |
| Inativar material | Não | Não | Não | Não | Sim | Apenas suporte/admin | Exige saldo físico e reservado zerados. |
| Operar movimentação de estoque | Não | Não | Não | Sim | Sim | Não | Apenas por operações formais: reserva, atendimento, devolução, saída excepcional, estorno ou SCPI conforme papel. |
| Ajustar estoque manualmente | Não | Não | Não | Não | Não | Não | Não há ajuste manual de estoque no MVP. |
| Registrar saída excepcional | Não | Não | Não | Não | Sim | Não | Apenas chefe de Almoxarifado; exige justificativa. |
| Consultar histórico de movimentações | Não | Não | Não | Sim | Sim | Apenas suporte/admin | Relatórios/históricos gerais são do Almoxarifado e suporte; histórico na requisição segue visibilidade da requisição. |
| Registrar devolução | Não | Não | Não | Sim | Sim | Não | Deve estar vinculada a requisição atendida ou parcialmente atendida. |
| Estornar requisição finalizada | Não | Não | Não | Não | Sim | Não | Apenas chefe de Almoxarifado; superusuário não realiza estorno operacional. |
| Estornar saída excepcional | Não | Não | Não | Não | Sim | Não | Apenas chefe de Almoxarifado. |
| Estornar devolução | Não | Não | Não | Não | Sim | Não | Apenas chefe de Almoxarifado e com saldo disponível suficiente. |
| Executar carga inicial técnica | Não | Não | Não | Não | Não | Apenas suporte/admin | No piloto pode ocorrer por script ou modo técnico controlado pelo administrador. |
| Executar importação SCPI | Não | Não | Não | Não | Não | Apenas suporte/admin | No MVP completo, importação por superusuário em comando, endpoint autenticado ou fluxo técnico. |
| Pré-visualizar importação | Não | Não | Não | Não | Não | Apenas suporte/admin | Deve validar tecnicamente sem persistir. |
| Confirmar importação com alertas | Não | Não | Não | Não | Não | Apenas suporte/admin | Exige confirmação explícita quando houver alertas/divergências. |
| Consultar histórico de importações | Não | Não | Não | Não | Sim | Apenas suporte/admin | Chefe de Almoxarifado consulta; superusuário acessa histórico completo. |
| Consultar divergências críticas | Não | Não | Não | Sim | Sim | Apenas suporte/admin | Divergências aparecem para gestão do Almoxarifado e suporte. |
| Receber notificações de suas requisições | Sim | Sim | Sim | Sim | Sim | Não | Criador e beneficiário recebem notificações conforme eventos. |
| Receber notificações de autorização pendente | Não | Não | Apenas próprio setor | Não | Apenas setor Almoxarifado | Não | Notificação deve ir para quem pode autorizar/recusar. |
| Receber notificações de atendimento | Sim | Sim | Sim | Sim | Sim | Não | Criador e beneficiário são notificados após atendimento. |
| Acessar relatórios gerais | Não | Não | Não | Sim | Sim | Apenas suporte/admin | Almoxarifado acessa relatórios do MVP; superusuário para suporte. |
| Acessar relatórios do próprio setor | Não | Não | Apenas próprio setor | Sim | Sim | Apenas suporte/admin | Chefe de setor acessa apenas consumo e requisições do próprio setor quando aplicável. |
| Exportar CSV de relatórios | Não | Não | Apenas próprio setor | Sim | Sim | Apenas suporte/admin | Exportação deve respeitar filtros e escopo do relatório. |
| Acessar painéis de gestão do Almoxarifado | Não | Não | Não | Não | Sim | Apenas suporte/admin | Superusuário acessa para suporte/importação/consulta, sem executar ações operacionais de estoque. |

## 5. Regras por papel

### 5.1 Solicitante

Todo usuário ativo é solicitante por padrão. O solicitante comum pode criar requisição para si mesmo, visualizar requisições em que seja criador ou beneficiário, editar rascunho quando for criador ou beneficiário, enviar para autorização, retornar para rascunho e cancelar nos estados permitidos.

Bloqueios principais:

- não cria requisição para terceiros;
- não visualiza requisições gerais do setor;
- não autoriza ou recusa requisições;
- não opera estoque;
- não acessa relatórios gerais;
- não executa importação SCPI nem rotinas administrativas.

### 5.2 Auxiliar de setor

O auxiliar de setor apoia funcionários do próprio setor. Pode criar requisições em nome de funcionários do setor principal do usuário e mantém as permissões de solicitante para suas próprias requisições.

Bloqueios principais:

- não atua em setores diferentes do seu;
- não autoriza nem recusa requisições;
- não opera estoque;
- não acessa relatórios gerais;
- não gerencia usuários, setores ou papéis.

### 5.3 Chefe de setor

O chefe de setor pode criar requisições em nome de funcionários do próprio setor, visualizar requisições do setor sob sua responsabilidade e autorizar ou recusar requisições cujo beneficiário pertença ao seu setor.

Bloqueios principais:

- não autoriza requisições de outros setores;
- não opera estoque;
- não edita rascunhos criados por funcionários do setor, salvo quando também for criador ou beneficiário da requisição;
- não cancela requisições de funcionários do setor apenas por ser chefe;
- não corrige nem reenvia requisições recusadas de terceiros;
- não acessa relatórios gerais, apenas relatórios do próprio setor quando aplicável.

### 5.4 Auxiliar de Almoxarifado

O auxiliar de Almoxarifado pode criar requisições em nome de qualquer funcionário, visualizar requisições de todos os setores, visualizar fila de atendimento, registrar atendimento total ou parcial, informar a pessoa que retirou fisicamente o material e registrar devoluções vinculadas a requisições atendidas ou parcialmente atendidas.

Bloqueios principais:

- não autoriza requisições;
- não registra saídas excepcionais;
- não realiza estornos operacionais;
- não executa importação SCPI;
- não gerencia usuários, setores ou papéis.

### 5.5 Chefe de Almoxarifado

O chefe de Almoxarifado herda as permissões operacionais do auxiliar de Almoxarifado. Também pode registrar saídas excepcionais, realizar estornos operacionais, inativar materiais quando saldo físico e saldo reservado estiverem zerados e consultar histórico de importações CSV.

Como chefe do setor Almoxarifado, pode autorizar ou recusar requisições cujo beneficiário pertença ao setor de Almoxarifado. Essa condição não permite autorizar requisições de outros setores.

Bloqueios principais:

- não autoriza requisições de setores diferentes do setor Almoxarifado;
- não gerencia usuários, setores e papéis como rotina administrativa estrutural;
- não faz ajuste manual de estoque;
- não edita ou exclui movimentações já registradas; correções ocorrem por estorno ou fluxo formal.

### 5.6 Superusuário

O superusuário atua em administração técnica e suporte estrutural. Pode importar materiais via CSV, gerenciar usuários, setores, perfis e configurações, consultar relatórios para suporte/administração e acessar rotinas técnicas compatíveis com esse papel.

Permissões técnicas/admin:

- executar importação SCPI em comando, endpoint autenticado ou fluxo técnico controlado;
- pré-visualizar importação e confirmar aplicação com alertas;
- gerenciar usuários, setores, chefes, auxiliares, papéis e configurações;
- consultar histórico completo de importações;
- acessar painéis e relatórios para suporte técnico/administração.

Bloqueios principais:

- não deve atuar como operador comum em nome de outros usuários;
- não deve operar estoque no dia a dia;
- não deve registrar retirada, devolução, saída excepcional ou estorno operacional;
- não deve realizar estornos operacionais quando a regra indicar que apenas chefe de Almoxarifado realiza;
- não deve reabrir requisição encerrada;
- não deve excluir registros operacionais.

## 6. Regras de visibilidade

- **Requisição própria:** criador pode visualizar a requisição e sua linha do tempo completa.
- **Requisição em que é beneficiário:** beneficiário pode visualizar a requisição e sua linha do tempo completa.
- **Requisições do setor:** chefe de setor visualiza requisições do setor sob sua responsabilidade.
- **Todas as requisições:** auxiliares de Almoxarifado e chefe de Almoxarifado visualizam requisições de todos os setores; superusuário pode visualizar para suporte/administração.
- **Fila de autorização:** chefe de setor visualiza apenas requisições `aguardando autorização` cujo beneficiário pertence ao seu setor; chefe de Almoxarifado visualiza apenas as do setor Almoxarifado.
- **Fila de atendimento:** auxiliares de Almoxarifado e chefe de Almoxarifado visualizam requisições `autorizada`.
- **Histórico/timeline:** todo usuário com permissão de visualizar a requisição deve ver a linha do tempo completa da requisição.
- **Relatórios:** funcionários do Almoxarifado e chefe de Almoxarifado acessam relatórios do MVP; chefe de setor acessa apenas relatórios de consumo e requisições do próprio setor; solicitante comum não acessa relatórios gerais; superusuário acessa para suporte técnico/administração.
- **Histórico de importação:** superusuário acessa o histórico completo; chefe de Almoxarifado pode consultar o histórico.
- **Materiais e divergências críticas:** materiais podem ser consultados pelos usuários conforme fluxos de requisição e relatórios; divergências críticas devem aparecer para gestão do Almoxarifado e suporte técnico/administração.

## 7. Regras de teste por permissão

- Testar caminho permitido por papel.
- Testar ação negada por papel.
- Testar ação negada por setor.
- Testar objeto fora do escopo.
- Testar usuário inativo.
- Testar superusuário em ação técnica.
- Testar superusuário bloqueado em ação operacional quando aplicável.
- Testar policy chamada pela view e pelo service.
- Testar `403 permission_denied` versus `404 not_found` conforme contrato.
- Testar que services revalidam autorização em toda escrita, mesmo quando a view já chamou policy.
- Testar que permissões de Almoxarifado não autorizam requisições de outros setores.
- Testar que a requisição usa setor do beneficiário, não setor do criador.
- Testar que relatórios e exportações respeitam filtros e escopo do usuário.

## 8. Pontos a confirmar

- A carga inicial SCPI do piloto pode ser executada por script ou modo técnico controlado pelo administrador; no MVP completo, a importação deve ser executada pelo superusuário por comando, endpoint autenticado ou fluxo técnico controlado. A implementação deve explicitar qual superfície técnica será usada em cada fase.
- A documentação indica consulta de materiais e observações internas como visíveis aos usuários, mas restringe relatórios gerais e histórico operacional amplo ao Almoxarifado/suporte. Endpoints de detalhe de material devem declarar explicitamente se o histórico de movimentações completo aparece para todos os usuários autenticados ou apenas para papéis operacionais/admin.
