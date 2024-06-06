"""
Django settings used in tests.
"""

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
    }
}

ROOT_URLCONF = __name__
urlpatterns = []  # type: ignore
