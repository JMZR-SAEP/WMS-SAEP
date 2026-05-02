# PR notificacoes fluxo

Branch: `feat/notificacoes-fluxo`.

Escopo implementado:
- `PIL-BE-NOT-001`: novo app `apps/notifications` com `Notificacao`, tipos de notificacao do fluxo principal, destinatario individual ou por papel operacional, status lida/nao lida, objeto relacionado por `GenericForeignKey`, admin e services para criar notificacoes e marcar como lida.
- `PIL-BE-NOT-002`: eventos essenciais do fluxo principal geram notificacoes pos-commit via `apps/core/events.py`, sem tornar notificacao fonte de verdade do dominio.
- Eventos publicados por `apps/requisitions/services.py`: envio para autorizacao, autorizacao, recusa, cancelamento e atendimento total/parcial.
- Destinatarios atuais: chefe do setor no envio; criador/beneficiario em autorizacao, recusa, cancelamento e atendimento; papeis `AUXILIAR_ALMOXARIFADO` e `CHEFE_ALMOXARIFADO` quando requisicao e autorizada.

Invariantes:
- Domain services publicam eventos com `publish_on_commit()`; handlers de notificacao rodam depois do commit.
- `apps/core/events.publish()` captura/loga excecoes de subscribers para evitar que side effects posteriores quebrem a operacao principal.
- Notificacoes permanecem side effects. Nao devem decidir sucesso de requisicao, autorizacao, cancelamento, atendimento ou estoque.
- Migrations continuam efemeras; apenas `apps/notifications/migrations/__init__.py` deve ser versionado para o app participar do fluxo de `makemigrations`/`migrate`.

Validacao local:
- `rtk make setup` passou apos adicionar o pacote de migrations do novo app.
- `rtk ruff check apps/core/events.py apps/notifications apps/requisitions/services.py tests/notifications/test_notifications.py tests/test_bootstrap.py` passou.
- `rtk make test` passou com 312 testes coletados.
