import os

import django
import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup Django before tests run."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    django.setup()
