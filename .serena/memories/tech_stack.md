# Tech stack

Current active stack for ERP-SAEP:
- Python compatible with Django 6.
- Django 6 monolith.
- Django REST Framework for APIs.
- PostgreSQL as the required database for pilot/production behavior.
- Django ORM.
- drf-spectacular for OpenAPI schema.
- django-filter for typed list endpoint filters.
- django-allauth for auth support.
- pytest, pytest-django, ruff, coverage, and pre-commit as the initial quality/tooling base.
- factory_boy as the chosen standard for test data generation.

Current scope rule: frontend is not part of the active implementation scope. Work should focus on domain, persistence, authentication, authorization, APIs, technical imports, administrative/internal flows, and tests. Do not introduce server-rendered UI work, SPA frameworks, or dedicated frontend components unless a later technical decision explicitly reopens that scope.

Typing/tooling rule: mypy, django-stubs, and djangorestframework-stubs are intentionally out of the current stack and may be reconsidered later if static typing becomes an explicit project discipline.

Async rule: Celery is not in the pilot critical path, and no Redis dependency is part of the current stack definition. Keep CSV import as a reusable domain service so async infrastructure can be added later without duplicating business logic.

Production shape under consideration:
- Nginx -> Gunicorn -> Django -> PostgreSQL.
- Docker Compose or Python/systemd deployment may be chosen later and should be recorded before production deployment.

Serena project config is set to language support: python, markdown, yaml.