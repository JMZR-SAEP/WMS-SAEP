# Matriz de Invariantes — ERP-SAEP

## 1. Objetivo

Este documento consolida os invariantes críticos de domínio do ERP-SAEP que não podem ser violados por `models`, `services`, `policies`, endpoints, comandos, admin actions, importações ou futuras interfaces.

A matriz conecta regra de negócio, camada de implementação esperada e testes obrigatórios. Ela deve ser usada como referência rápida antes de implementar, revisar ou aprovar mudanças que afetem usuários, setores, papéis, requisições, itens, estoque, movimentações, auditoria, importação SCPI CSV ou contratos de API.

## 2. Fontes de referência

Documentos lidos para consolidar esta matriz:

- `.serena/memories/project_overview.md`
- `AGENTS.md`
- `docs/design-acesso-ocasional/modelo-dominio-regras.md`
- `docs/design-acesso-ocasional/processos-almoxarifado.md`
- `docs/design-acesso-ocasional/criterios-aceite.md`
- `docs/design-acesso-ocasional/importacao-scpi-csv.md`
- `docs/design-acesso-rapido/api-contracts.md`
- `docs/backlog/backlog-tecnico-piloto.md`
- `docs/coderabbit-guidelines.md`

Em caso de conflito, prevalecem os documentos completos de domínio, processos, critérios de aceite e os guardrails do projeto. Sínteses operacionais devem ser atualizadas quando uma decisão posterior alterar regra de negócio já documentada.

## 3. Como usar esta matriz

Cada implementação deve verificar:

- invariante aplicável;
- camada responsável;
- service/policy esperado;
- tipo de teste obrigatório;
- critério de aceite relacionado.

Nenhuma mudança de contrato, regra crítica, status, saldo, reserva, histórico ou permissão contextual deve ser considerada completa sem teste que prove o caminho feliz e o bloqueio da violação correspondente.

## 4. Matriz resumida de invariantes

| ID | Tema | Invariante | Camada principal | Reforço esperado | Testes mínimos | Referências |
|---|---|---|---|---|---|---|
| USR-01 | Usuários, setores e papéis | Login deve ser feito por matrícula funcional única. | Model/Auth | Constraint de unicidade, manager/forms de autenticação | Login válido, matrícula duplicada, usuário inexistente | Modelo 2.1, Backlog PIL-BE-ACE-001/004 |
| USR-02 | Usuários, setores e papéis | CPF e telefone não são campos cadastrais permanentes do usuário. | Model/Importação de credencial | Ausência de campos permanentes; uso transitório do CPF apenas para senha inicial quando aplicável | Modelo não persiste CPF/telefone; criação/importação não retém CPF | Modelo 2.1, Backlog PIL-BE-ACE-001 |
| USR-03 | Usuários, setores e papéis | Usuário inativo não deve ser tratado como apto ao acesso ou à operação. | Auth/Policy | Bloqueio no fluxo de autenticação e nas policies | Login bloqueado; operação negada para inativo | Critérios 11.1, Backlog PIL-BE-ACE-004 |
| USR-04 | Usuários, setores e papéis | Todo usuário ativo é solicitante por padrão. | Policy | Policy de permissões derivada do usuário ativo | Usuário comum cria para si; não opera fora do papel | Modelo 2.2, Critérios 11.1 |
| USR-05 | Usuários, setores e papéis | Cada usuário pertence a um único setor. | Model | FK obrigatória para setor principal | Usuário sem setor inválido quando regra ativa; ausência de vínculos auxiliares | Modelo 2.1 |
| USR-06 | Usuários, setores e papéis | Todo setor possui chefe responsável e não pode ficar temporariamente sem chefe. | Model/Service | FK obrigatória; validação transacional em alteração de chefe | Criar setor com chefe; bloquear setor sem chefe | Modelo 2.1, Backlog PIL-BE-ACE-002 |
| USR-07 | Usuários, setores e papéis | Um chefe responde por apenas um setor. | Model/Policy | Constraint de unicidade sobre chefe responsável | Bloquear mesmo chefe em dois setores | Modelo 2.1, Backlog PIL-BE-ACE-002 |
| USR-08 | Usuários, setores e papéis | Setor inativo permanece em histórico, mas não recebe nova requisição. | Service/Policy | Bloqueio na criação; preservação de FKs históricas | Criar para setor ativo; negar para setor inativo; histórico continua consultável | Modelo 2.1 |
| PER-01 | Permissões e escopo | Solicitante cria requisição apenas para si. | Policy/Service | `can_create_request_for(actor, beneficiary)` compartilhada | Caminho feliz próprio; permissão negada para terceiro | Critérios 11.1, Backlog PIL-BE-ACE-005 |
| PER-02 | Permissões e escopo | Auxiliar de setor atua apenas no próprio setor. | Policy/Service | Escopo pelo setor principal do usuário | Criar para mesmo setor; negar outro setor; não autorizar; não operar estoque | Modelo 2.2, Critérios 11.2 |
| PER-03 | Permissões e escopo | Chefe de setor autoriza apenas requisições do setor do beneficiário. | Policy/Service | Policy por setor responsável | Autorizar próprio setor; negar outro setor | Critérios 2.1, 11.3 |
| PER-04 | Permissões e escopo | Almoxarifado pode criar em nome de qualquer funcionário. | Policy/Service | Papel operacional de almoxarifado | Criar para setores distintos; preservar setor do beneficiário | Modelo 2.2, Critérios 1.1 |
| PER-05 | Permissões e escopo | Chefe de almoxarifado herda permissões operacionais do auxiliar de almoxarifado. | Policy | Composição explícita de permissões | Registrar atendimento/devolução como chefe; autorizar apenas setor Almoxarifado quando chefe do setor | Modelo 2.2, Critérios 11.5 |
| PER-06 | Permissões e escopo | Superusuário atua em administração técnica, não em operação cotidiana de estoque. | Policy/Admin | Bloqueio de retirada, devolução, saída excepcional e estorno operacional | Permitir cadastros/importação; negar operação de estoque | Modelo 2.3, Critérios 11.6 |
| PER-07 | Permissões e escopo | Requisição sempre pertence ao setor do beneficiário, não ao setor do criador. | Service/Model snapshot | Snapshot `setor_beneficiario` na criação | Almoxarifado cria para Obras e autorização vai para chefe de Obras | Critérios 1.2, Modelo 2.2 |
| PER-08 | Permissões e escopo | Views e services devem chamar a mesma policy quando houver autorização contextual. | View/Service/Policy | Policy centralizada em `policies.py` ou equivalente | Teste de view e service para escopo negado; sem duplicação em serializer | AGENTS, API contracts, CodeRabbit |
| REQ-01 | Requisições | Toda requisição começa em rascunho. | Service/Model | Default controlado pelo service de criação | Criação gera `rascunho` | Processos 1.3, Critérios 1.1 |
| REQ-02 | Requisições | Rascunho nunca enviado não possui número público. | Service/Model | Número nulo até primeiro envio | Criar rascunho sem número; descarte não consome número | Critérios 1.1, 1.9 |
| REQ-03 | Requisições | Número público só é gerado no primeiro envio e segue `REQ-AAAA-NNNNNN`. | Service transacional | Gerador anual único e atômico | Primeiro envio gera formato correto e sequência anual | Modelo 2.1, Critérios 1.6 |
| REQ-04 | Requisições | Reenvios preservam o mesmo número público. | Service de transição | Campo histórico imutável após primeiro envio | Retorno para rascunho e reenvio mantêm número | Processos 1.4, Critérios 1.7 |
| REQ-05 | Requisições | Requisição precisa ter pelo menos um item. | Service/Serializer | Validação de payload e regra crítica no service | Bloquear criação/salvamento/envio sem item | Modelo 2.1, Critérios 1.1 |
| REQ-06 | Requisições | Após envio para autorização, não há edição direta de itens. | Service/Policy | Máquina de estados impede mutação direta fora de rascunho | Bloquear edição em `aguardando autorização`; permitir retorno para rascunho | Processos 1.4, Critérios 1.8 |
| REQ-07 | Requisições | Requisição registra criador, beneficiário e setor do beneficiário. | Service/Model snapshot | Campos obrigatórios e snapshots protegidos | Criar em nome de terceiro preservando os três papéis | Modelo 2.1, Critérios 1.1 |
| REQ-08 | Requisições | Linha do tempo registra eventos principais e é visível a usuários autorizados. | Service/API | Eventos auditáveis e serializer de timeline | Eventos de criação/envio/autorização/atendimento; acesso autorizado vê timeline completa | Modelo 2.1, Critérios 9 |
| REQ-09 | Requisições | Cópia recalcula saldo e não copia quantidades autorizadas/entregues. | Service | Cópia cria novo rascunho, novo criador e sem número | Copiar atendida/parcial; bloquear item sem saldo/divergente; não copiar autorização/entrega | Modelo 2.1, Critérios 1.13 |
| ITEM-01 | Itens de requisição | Quantidade autorizada nunca maior que solicitada. | Service/Model constraint | Validação de domínio e constraint quando possível | Bloquear autorização acima da solicitada | Modelo 2.1, Critérios 2 |
| ITEM-02 | Itens de requisição | Quantidade entregue nunca maior que autorizada. | Service/Model constraint | Validação no atendimento | Bloquear entrega acima da autorizada | Modelo 2.1, Critérios 3 |
| ITEM-03 | Itens de requisição | Autorização parcial exige justificativa. | Service/Serializer | Justificativa obrigatória por item parcial | Autorizar menor com justificativa; bloquear sem justificativa | Critérios 2.3 |
| ITEM-04 | Itens de requisição | Atendimento parcial exige justificativa. | Service/Serializer | Justificativa obrigatória por item entregue abaixo do autorizado | Entregar menor com justificativa; bloquear sem justificativa | Critérios 3.3 |
| ITEM-05 | Itens de requisição | Item com autorização zero exige justificativa. | Service/Serializer | Justificativa obrigatória por item zerado | Autorizar zero com justificativa; bloquear sem justificativa | Critérios 2.4 |
| ITEM-06 | Itens de requisição | Atendimento com entrega zero exige justificativa quando o item tinha quantidade autorizada maior que zero. | Service/Serializer | Justificativa obrigatória; sem baixa física | Entrega zero com justificativa; item autorizado zero não exige entrega | Critérios 3.4, 3.5 |
| ITEM-07 | Itens de requisição | Requisição autorizada precisa ter ao menos um item com quantidade autorizada maior que zero. | Service | Regra agregada na autorização | Bloquear todos os itens zerados; orientar recusa | Critérios 2.5 |
| ITEM-08 | Itens de requisição | Requisição atendida ou atendida parcialmente precisa ter ao menos um item com quantidade entregue maior que zero. | Service | Regra agregada no atendimento | Bloquear finalização sem entrega; orientar cancelamento com justificativa | Critérios 3.6 |
| EST-01 | Estoque | Saldo físico e saldo reservado são armazenados; saldo disponível é calculado como físico menos reservado. | Model/Service | Propriedade calculada; não persistir disponibilidade como fonte de verdade | Cálculo correto após reserva, retirada e liberação | Modelo 2.3, Critérios 7.2 |
| EST-02 | Estoque | Autorização reserva estoque, mas não baixa saldo físico. | Service transacional | Movimentação de reserva por autorização | Autorizar aumenta reservado e mantém físico | Modelo 2.3, Critérios 2.2 |
| EST-03 | Estoque | Retirada consome reserva e baixa saldo físico. | Service transacional | Movimentação de saída por requisição | Atendimento baixa físico e reduz reservado | Modelo 2.3, Critérios 3.2 |
| EST-04 | Estoque | Reserva não entregue deve ser liberada. | Service transacional | Movimentação de liberação por atendimento parcial/cancelamento | Atendimento parcial/cancelamento libera saldo reservado | Processos 1.3, Critérios 3.3 |
| EST-05 | Estoque | Não pode haver reserva acima do saldo disponível. | Service transacional | Recalcular saldo dentro do lock antes de reservar | Bloquear reserva acima do saldo; concorrência entre autorizações | Critérios 2.8, 2.9 |
| EST-06 | Estoque | Operações críticas de saldo usam transação atômica e lock. | Service | `transaction.atomic()`, `select_for_update()`, ordem determinística de locks | Teste PostgreSQL de concorrência; idempotência quando aplicável | AGENTS, CodeRabbit |
| EST-07 | Estoque | Divergência crítica ocorre quando saldo físico fica menor que saldo reservado. | Service/Model | Marcador derivado/recalculado | Importação reduz físico abaixo do reservado e marca divergência | Modelo 2.3, Critérios 7.3 |
| EST-08 | Estoque | Material com divergência crítica bloqueia novas requisições e autorizações. | Policy/Service | Bloqueio na seleção e na autorização | Bloquear criação e autorização de material divergente | Importação SCPI 8, Critérios 1.5, 2.11 |
| EST-09 | Estoque | Divergência crítica se resolve automaticamente quando físico fica maior ou igual ao reservado. | Service | Recalcular após importação, cancelamento, atendimento parcial ou estorno | Resolver alerta e liberar fluxos quando houver saldo disponível | Importação SCPI 8, Critérios 7.4 |
| EST-10 | Estoque | Material inativo não pode ser usado em nova requisição. | Service/QuerySet | Busca operacional exclui inativos; histórico preserva | Bloquear seleção; manter histórico consultável | Modelo 2.1, Critérios 7.1 |
| EST-11 | Estoque | Material só pode ser inativado com saldo físico e reservado zerados. | Service/Policy | Validação de saldo antes de inativar | Permitir zerado; bloquear com físico ou reservado | Modelo 2.3, Critérios 7.5, 7.6 |
| EST-12 | Estoque | Não há ajuste manual de estoque no MVP. | Service/Admin | Sem endpoint/admin action de ajuste manual; correção via SCPI/importação ou operação formal | Ausência de fluxo manual; tentativa negada quando existir superfície admin/API | Modelo 2.3, Backlog |
| AUD-01 | Movimentações, auditoria e histórico | Movimentações de estoque são histórico/auditoria. | Model/Service | Ledger com saldo anterior/posterior e origem | Movimentação gerada para reserva, saída, liberação, SCPI, devolução e estorno | Modelo 2.3, CodeRabbit |
| AUD-02 | Movimentações, auditoria e histórico | Movimentações já registradas não devem ser editadas/excluídas diretamente. | Model/Admin/Service | Imutabilidade de ledger; bloqueio de update/delete | Bloquear edição/exclusão; correção por lançamento compensatório | Modelo 2.3, CodeRabbit |
| AUD-03 | Movimentações, auditoria e histórico | Correções de requisições finalizadas ocorrem por estorno. | Service | Estorno preserva histórico e encerra requisição | Estorno total/parcial; requisição estornada não reabre | Modelo 2.4, Critérios 6 |
| AUD-04 | Movimentações, auditoria e histórico | Timeline deve expor eventos a usuários autorizados. | API/Policy | Serializer de timeline e policy de visualização | Usuário autorizado vê eventos completos; fora de escopo não vê recurso | Modelo 2.1 |
| AUD-05 | Movimentações, auditoria e histórico | Side effects devem ocorrer após commit quando aplicável. | Events/Service | `publish_on_commit()` ou equivalente | Falha de notificação não desfaz operação principal; evento só após commit | AGENTS, CodeRabbit |
| AUD-06 | Movimentações, auditoria e histórico | Notificações não decidem o sucesso da transação principal. | Events/Notifications | Notificação desacoplada do domínio | Operação conclui mesmo com side effect falho; histórico operacional preservado | Modelo 2.3, CodeRabbit |
| SCPI-01 | SCPI CSV | SCPI é fonte oficial de dados cadastrais de materiais e correção de saldo físico. | Import Service/Model | Dados oficiais atualizados pela importação | Importação cria/atualiza material e saldo físico conforme CSV | Importação SCPI 1, 6 |
| SCPI-02 | SCPI CSV | ERP-SAEP não edita diretamente dados cadastrais oficiais vindos do SCPI. | Model/Admin/API | Campos oficiais read-only nas superfícies locais | Bloquear edição local de nome, descrição, grupo, subgrupo, sequencial e unidade | Modelo 2.1, Importação SCPI |
| SCPI-03 | SCPI CSV | Importação aceita UTF-8 com BOM e separador `;`. | Import Service | Leitor CSV configurado para BOM e `;` | Arquivo válido com BOM é lido corretamente | Importação SCPI 2, Critérios 8.1 |
| SCPI-04 | SCPI CSV | Linhas sem código são continuação da descrição anterior. | Import Normalizer | Reconstrução de produto lógico | Descrição quebrada em múltiplas linhas vira um material lógico | Importação SCPI 4, Critérios 8.1 |
| SCPI-05 | SCPI CSV | Importação possui regra tudo ou nada para erro técnico impeditivo. | Import Service transacional | `atomic()` envolvendo aplicação completa | Erro técnico não persiste material, grupo, subgrupo, estoque ou movimentação | Importação SCPI 11, Critérios 8.3 |
| SCPI-06 | SCPI CSV | Alertas e divergências não são erros impeditivos. | Import Service | Prévia separa erros de alertas | Aplicar com confirmação explícita e status concluída com alertas | Importação SCPI 9, Critérios 8.4 |
| SCPI-07 | SCPI CSV | Material ausente no CSV não é inativado automaticamente. | Import Service | Lista de ausentes sem ação automática | Ausente aparece para análise e permanece ativo/inativo como estava | Importação SCPI 7, Critérios 8.7 |
| SCPI-08 | SCPI CSV | `QUAN3` atualiza saldo físico. | Import Service/Estoque | Movimentação de atualização via SCPI | Alteração de `QUAN3` atualiza físico e registra saldo anterior/novo/diferença | Importação SCPI 6, Critérios 8.5 |
| SCPI-09 | SCPI CSV | Divergência crítica gerada por importação não cancela reservas automaticamente. | Import Service/Estoque | Bloqueio futuro sem apagar reservas existentes | Importar físico menor que reservado mantém reservas e bloqueia novas requisições/autorizações | Importação SCPI 8 |
| API-01 | API e contratos | Endpoints formais ficam em `/api/v1/`. | URL/API | Versionamento explícito | Rotas formais sob `/api/v1/` | API contracts 1 |
| API-02 | API e contratos | Todo endpoint declara autenticação, autorização, entrada, saída, status, erros, paginação/filtros e OpenAPI. | View/API Schema | `@extend_schema`, serializers de input/output, permission classes | Teste de contrato e schema para endpoint novo/alterado | API contracts 2, 6, 8 |
| API-03 | API e contratos | Serializers validam formato e coerência local; services contêm regra crítica de domínio. | Serializer/Service | Views e serializers finos | Violação crítica falha no service; payload inválido falha no serializer | API contracts 2, CodeRabbit |
| API-04 | API e contratos | Erros usam envelope padrão. | Exception Handler | Handler global em `apps/core/api/exceptions.py` | Erro de validação, permissão, domínio e inesperado seguem envelope | API contracts 5 |
| API-05 | API e contratos | Conflitos de domínio usam `409 domain_conflict`. | Service/API | Exceção de domínio HTTP-safe | Saldo insuficiente, transição inválida ou estado conflitante retornam 409 | API contracts 5, 8 |
| API-06 | API e contratos | Listas usam paginação padrão. | Pagination/API | `StandardPageNumberPagination` | Lista retorna envelope com `count`, `page`, `page_size`, `total_pages`, `next`, `previous`, `results` | API contracts 4 |

## 5. Invariantes detalhados por tema

### 5.1 Usuários, setores e papéis

Usuários representam funcionários com acesso ao ERP-SAEP e devem ser identificados pela matrícula funcional. CPF e telefone não fazem parte do cadastro permanente; qualquer uso de CPF para senha inicial deve ser transitório.

Cada usuário pertence a um único setor, e cada setor precisa ter chefe responsável. A relação chefe-setor é exclusiva: um chefe não pode responder por mais de um setor. Setores inativos permanecem em registros históricos, relatórios antigos e requisições antigas, mas são inválidos para novas requisições.

Na implementação Django, esses invariantes pertencem principalmente aos models de usuários/setores, constraints e services de manutenção cadastral. Policies devem derivar permissões a partir de usuário ativo, setor principal e papéis atribuídos, sem criar vínculos auxiliares entre usuários e outros setores no MVP.

### 5.2 Permissões e escopo

As permissões operacionais dependem do papel e do setor do beneficiário. Solicitantes criam apenas para si, auxiliares de setor atuam apenas no próprio setor, chefes autorizam apenas requisições do setor sob sua responsabilidade e funcionários do Almoxarifado podem criar em nome de qualquer funcionário.

O chefe de Almoxarifado herda as permissões operacionais do auxiliar de Almoxarifado e também atua como chefe do setor de Almoxarifado. O superusuário é reservado para administração técnica, importações e cadastros estruturais; ele não deve operar estoque no dia a dia.

Qualquer autorização contextual deve estar centralizada em `policies.py` ou módulo equivalente. Views e services devem chamar a mesma policy, especialmente em escritas e transições de estado, para evitar divergência entre contrato HTTP e regra de domínio.

### 5.3 Requisições

Toda requisição nasce como `rascunho`, com criador, beneficiário e setor do beneficiário registrados. O setor da requisição nunca é inferido do criador quando o criador age em nome de outra pessoa.

Rascunhos nunca enviados não possuem número público. O número `REQ-AAAA-NNNNNN` só é gerado no primeiro envio para autorização, com sequência anual, e deve ser preservado em retornos para rascunho, reenvios, cancelamentos e consultas históricas.

Depois do envio para autorização, itens não podem ser editados diretamente. Alterações exigem retorno para rascunho quando a regra permitir. A linha do tempo deve registrar eventos principais, como criação, envio, retorno para rascunho, recusa, autorização, cancelamento, atendimento, devolução e estorno, e deve ser visível integralmente aos usuários autorizados a visualizar a requisição.

A cópia de requisição é uma nova criação: gera rascunho sem número público, com novo criador e nova data, recalcula saldo disponível atual e copia apenas quantidades solicitadas. Quantidades autorizadas e entregues nunca são copiadas.

### 5.4 Itens de requisição

Cada item preserva três quantidades distintas: solicitada, autorizada e entregue. A quantidade autorizada não pode exceder a solicitada; a quantidade entregue não pode exceder a autorizada.

Autorizações parciais, autorizações zeradas por item e atendimentos parciais exigem justificativa. Entrega zero exige justificativa quando o item tinha quantidade autorizada maior que zero. Item autorizado com quantidade zero não gera baixa, não consome reserva e não exige quantidade entregue.

Uma requisição não pode ser autorizada com todos os itens zerados; nesse caso, deve ser recusada. Uma requisição não pode ser finalizada como atendida ou atendida parcialmente se nenhum item teve quantidade entregue maior que zero; nesse caso, a requisição autorizada deve ser cancelada com justificativa.

### 5.5 Estoque

O estoque separa saldo físico, saldo reservado e saldo disponível. Saldo físico e reservado são armazenados; saldo disponível é cálculo dinâmico de `saldo físico - saldo reservado`.

A autorização reserva estoque e não baixa saldo físico. A retirada consome a reserva correspondente e baixa o saldo físico apenas na quantidade efetivamente entregue. Qualquer reserva autorizada e não entregue deve ser liberada por atendimento parcial ou cancelamento.

Operações críticas de saldo e reserva devem ocorrer em `transaction.atomic()`, com `select_for_update()` na linha agregadora de saldo e ordem determinística de locks quando houver múltiplos materiais. Testes de concorrência em PostgreSQL são obrigatórios para autorização, atendimento, estorno ou qualquer fluxo que possa disputar saldo.

Divergência crítica ocorre quando o saldo físico fica menor que o saldo reservado. Materiais nessa condição bloqueiam novas requisições e autorizações, mas não cancelam reservas automaticamente. A divergência se resolve automaticamente quando o saldo físico volta a ser maior ou igual ao reservado.

Material inativo permanece em histórico, mas não entra em nova requisição ou nova entrada de estoque. A inativação só é permitida quando saldo físico e saldo reservado estiverem zerados. O MVP não possui ajuste manual de estoque; correções de saldo físico vêm do SCPI ou de operações formais já definidas.

### 5.6 Movimentações, auditoria e histórico

Movimentações de estoque são ledger e trilha de auditoria. Elas explicam reservas, liberações, saídas por requisição, saldos iniciais, devoluções, saídas excepcionais, estornos e atualizações via SCPI.

Registros históricos e ledgers auditáveis são imutáveis: não devem ser editados, excluídos ou sobrescritos após criação. Correções devem criar movimentação compensatória ou operação formal, como estorno, reimportação CSV ou inativação controlada.

Side effects, como notificações, e-mails, webhooks ou integrações externas, não são fonte de verdade e não decidem o sucesso da transação principal. Quando aplicável, devem ser disparados após commit por evento, por exemplo com `publish_on_commit()`.

### 5.7 SCPI CSV

O SCPI é a fonte oficial dos dados cadastrais de materiais e da correção de saldo físico. O ERP-SAEP pode armazenar e usar esses dados operacionalmente, mas não edita diretamente campos oficiais vindos do SCPI, como nome, descrição, grupo, subgrupo, sequencial, unidade de medida e saldo físico por ajuste manual.

A importação deve aceitar CSV UTF-8 com BOM e separador `;`. Descrições quebradas em múltiplas linhas físicas devem ser reconstruídas: uma nova linha lógica começa quando a linha inicia com código no padrão `000.000.000;`; linhas sem código são continuação da descrição anterior.

Erros técnicos impeditivos seguem regra tudo ou nada: nenhuma alteração de material, grupo, subgrupo, estoque ou movimentação deve ser persistida. Alertas, materiais ausentes, saldos atualizados e divergências críticas não são erros impeditivos quando o arquivo foi lido e validado tecnicamente.

Materiais ausentes no CSV não são inativados automaticamente. O campo `QUAN3` atualiza o saldo físico e deve registrar evento de atualização via SCPI com saldo anterior, saldo novo, diferença, data/hora e usuário responsável. Se a importação gerar divergência crítica, reservas existentes continuam preservadas e o bloqueio vale para novas requisições e autorizações.

### 5.8 API e contratos

Endpoints formais pertencem a `/api/v1/` e devem seguir Django REST Framework com contrato explícito. Todo endpoint novo ou alterado precisa declarar autenticação, autorização, entrada, saída, status HTTP, envelope de erro, paginação/filtros quando aplicável e schema OpenAPI.

Serializers validam formato, tipos, coerência local do payload e representação. Regras críticas de domínio, transições de estado, autorização contextual e mutações transacionais pertencem a services e policies.

Erros devem usar o envelope padrão. Violações de domínio, como saldo insuficiente, transição inválida, estado atual incompatível ou conflito de saldo, devem retornar `409 domain_conflict`. Listas devem usar a paginação padrão documentada em `api-contracts.md`.

## 6. Checklist para PRs

- O PR altera algum invariante?
- A documentação canônica foi atualizada?
- Existe teste para caminho feliz?
- Existe teste para permissão negada?
- Existe teste para violação de domínio?
- Existe teste para concorrência quando envolve estoque/reserva?
- O contrato OpenAPI foi atualizado quando endpoint mudou?
