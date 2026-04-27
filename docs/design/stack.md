

# Stack Técnica — ERP-SAEP

## 1. Visão geral

O ERP-SAEP será implementado como uma aplicação web monolítica baseada em Django.

A stack foi escolhida para favorecer:

- desenvolvimento rápido do piloto;
- regras de negócio centralizadas no backend;
- contratos HTTP claros para APIs;
- foco inicial exclusivo em backend e integrações técnicas;
- implantação em servidor próprio;
- segurança transacional para estoque e requisições.

## 2. Backend

Stack principal:

- Python compatível com Django 6.
- Django 6.
- PostgreSQL.
- Django ORM.
- Django REST Framework.
- drf-spectacular.
- django-filter.
- django-allauth.

O sistema deve priorizar uma arquitetura monolítica Django com backend/API-first, mantendo regras de negócio no backend e contratos HTTP explícitos.

## 3. Frontend

No momento, frontend não faz parte do escopo ativo do ERP-SAEP.

A implementação atual deve se concentrar em domínio, persistência, autenticação, autorização, APIs, importações técnicas e rotinas administrativas operadas por comando, admin do Django ou endpoints internos.

Não devem ser implementadas telas server-rendered, SPA separada, componentes de frontend dedicados ou trabalho de UX/UI enquanto essa diretriz estiver vigente.

Se uma interface vier a ser necessária no futuro, a decisão deve ser registrada separadamente com escopo, tecnologia escolhida, impacto no contrato da API e estratégia de testes.

## 4. Django REST Framework

Django REST Framework faz parte da stack atual e deve ser usado para endpoints de API.

Diretrizes:

- usar serializers para validação de entrada, tipos, coerência local do payload e representação de saída;
- manter ViewSets e APIViews finos;
- concentrar regra de domínio crítica em services ou use cases;
- usar permissions para acesso geral e escopo de objeto quando aplicável;
- versionar endpoints sob `/api/v1/` quando estabilizados para consumo público ou interno formal;
- manter schema com drf-spectacular coerente com os contratos implementados;
- usar `django-filter` para filtros tipados em endpoints de lista;
- cobrir mudanças de contrato de API com testes.

Nenhum endpoint novo ou alterado deve ser considerado completo sem definição clara de autenticação, autorização, serializer de entrada, serializer de saída, permissões por papel e escopo, códigos de status esperados, formato de erro, paginação, filtros e ordenação quando aplicáveis.

O padrão canônico de contratos HTTP, respostas de sucesso, envelope de erro, paginação, filtros, autenticação e OpenAPI está em `docs/design/api-contracts.md`.

## 5. Banco de dados

O banco principal será PostgreSQL desde o início.

PostgreSQL é obrigatório para o piloto real porque o ERP-SAEP depende de:

- transações confiáveis;
- integridade relacional;
- locks de linha;
- controle de concorrência na reserva de estoque;
- relatórios operacionais;
- auditoria e histórico.

SQLite não deve ser usado para ambiente de piloto real ou produção.

Operações críticas de estoque devem usar transações atômicas, especialmente:

- autorização de requisição;
- reserva de estoque;
- atendimento e baixa de estoque;
- liberação de reserva;
- devolução;
- saída excepcional;
- estorno;
- importação CSV que altere materiais ou saldos.

Quando houver risco de concorrência sobre o mesmo estoque, usar bloqueio transacional adequado, como `select_for_update()`.

## 6. Autenticação e usuários

A autenticação será local, usando matrícula funcional e senha.

O projeto deve usar usuário customizado desde o início.

Diretriz recomendada:

- usar a matrícula funcional como identificador de login;
- manter matrícula única;
- não manter CPF como campo cadastral permanente;
- não manter telefone como campo cadastral permanente;
- usar os mecanismos de senha, sessão e permissões do Django sempre que possível.

O modelo de usuário deve estar alinhado às regras de `docs/design/modelo-dominio-regras.md` e aos critérios de aceite de permissões.

## 7. Importação SCPI CSV

A importação SCPI CSV deve ser implementada como serviço de domínio reutilizável.

Estrutura recomendada:

```text
imports/
  services/
    normalize_scpi_csv.py
    preview_import.py
    apply_import.py
```

O mesmo núcleo de importação deve poder ser chamado por:

- comando de management;
- endpoint técnico/autenticado, se necessário;
- task assíncrona futura, se necessário.

No piloto, a carga inicial pode ser feita por comando de management ou fluxo técnico controlado.

Se no futuro houver uma interface operacional para importação, ela deve possuir:

- upload do CSV;
- normalização;
- pré-visualização;
- confirmação explícita quando houver alertas;
- aplicação transacional;
- histórico de importação.

## 8. Tarefas assíncronas

Celery não faz parte da stack atual e não é obrigatório no piloto.

A decisão inicial é:

- não colocar Celery no caminho crítico do piloto;
- manter a importação CSV como serviço reutilizável;
- permitir que Celery seja adicionado depois sem reescrever a regra de importação.

Usar processamento síncrono quando:

- a carga for controlada;
- o arquivo CSV for pequeno ou médio;
- o processamento não causar timeout;
- a operação for executada por usuário técnico ou superusuário.

Considerar infraestrutura assíncrona dedicada no futuro quando:

- arquivos CSV ficarem grandes;
- importações começarem a causar timeout;
- houver reimportações frequentes;
- relatórios pesados precisarem ser gerados fora do ciclo HTTP;
- houver necessidade de tarefas agendadas;
- houver notificações externas futuras.

Se Celery ou equivalente for adotado no futuro, ele deve processar tarefas de infraestrutura, não conter regra de negócio duplicada.

## 9. Infraestrutura

O ERP-SAEP rodará em servidor próprio.

Arquitetura recomendada de produção:

```text
Nginx
  -> Gunicorn
    -> Django
      -> PostgreSQL
```

Componentes esperados:

- Nginx como reverse proxy.
- Gunicorn como servidor WSGI.
- PostgreSQL como banco de dados.
- Serviço Django isolado.
- HTTPS sempre que possível.
- Variáveis sensíveis fora do repositório.
- Logs de aplicação e servidor.

Docker Compose pode ser usado para desenvolvimento e também para produção, se a equipe decidir operar o servidor dessa forma.

Alternativa aceitável em produção:

- ambiente Python gerenciado no servidor;
- Gunicorn controlado por systemd;
- PostgreSQL instalado no servidor;
- Nginx como proxy.

A decisão final entre Docker Compose em produção ou systemd deve ser registrada antes da implantação.

## 10. Backups

Backups devem ser tratados como requisito operacional desde o início.

Obrigatório para piloto real e produção:

- backup automático diário do PostgreSQL;
- política de retenção definida;
- teste periódico de restauração;
- backup dos arquivos enviados, especialmente CSVs importados;
- documentação do procedimento de restauração.

O sistema não deve ser considerado pronto para uso real sem rotina mínima de backup e restauração testada.

## 11. Qualidade de código

Ferramentas recomendadas:

- pytest;
- pytest-django;
- ruff;
- coverage;
- pre-commit;
- factory_boy para dados de teste.

Diretrizes:

- escrever testes para regras de negócio críticas;
- priorizar testes de domínio e transições de status;
- testar concorrência de reserva de estoque;
- testar permissões por papel;
- testar importação CSV com casos reais e casos problemáticos;
- testar contratos de API quando endpoints DRF forem criados ou alterados;
- evitar regra de negócio relevante apenas em serializers, views ou JavaScript.

## 12. Organização sugerida de apps Django

A organização deve favorecer fronteiras claras de domínio e aproveitar a estrutura existente do cookiecutter-django.

Diretriz estrutural:

- os apps Django do projeto devem ficar sob a pasta `apps/`.
- a pasta `config/` permanece responsável por settings, URLs, ASGI/WSGI e bootstrap do projeto.

Estrutura atual relevante:

```text
config/
apps/
  users/
```

Não criar um novo app de usuários enquanto o app existente `apps/users/` puder ser adaptado às regras do ERP-SAEP.

Apps ou módulos de domínio podem ser criados conforme o escopo avançar:

- `organizational`: setores e vínculos organizacionais.
- `materials`: grupos, subgrupos e materiais.
- `stock`: saldos, reservas e movimentações de estoque.
- `requisitions`: cabeçalho, itens e ciclo geral da requisição.
- `approvals`: autorização, recusa e regras de reserva.
- `warehouse`: atendimento, retirada, devolução, saída excepcional e estorno.
- `notifications`: notificações internas.
- `reports`: relatórios e exportações CSV.
- `audit`: linha do tempo e eventos auditáveis.
- `imports`: importação SCPI CSV.

Essa divisão pode ser ajustada conforme o cookiecutter-django e o domínio real evoluírem, mas as fronteiras de domínio devem permanecer claras.
