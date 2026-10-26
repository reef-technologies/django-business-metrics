"""
Django settings used in tests.
"""

import tempfile
from pathlib import Path

DEBUG = True
SECRET_KEY = "DUMMY"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        # Django ignores close() on in-memory SQLite, and tests check that connections get closed.
        "TEST": {"NAME": str(Path(tempfile.gettempdir()) / "django_business_metrics_test.sqlite3")},
    }
}

ROOT_URLCONF = __name__
urlpatterns = []  # type: ignore
