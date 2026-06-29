"""Settings for local test runs (no Postgres required)."""

from .development import *  # noqa: F401, F403
from .development import MIDDLEWARE as DEVELOPMENT_MIDDLEWARE

MIDDLEWARE = [
    middleware
    for middleware in DEVELOPMENT_MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use simple static storage in tests — no collectstatic manifest needed
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
