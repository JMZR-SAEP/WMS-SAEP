from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_erp_saep",
        "USER": "saep",
        "PASSWORD": "saep",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
