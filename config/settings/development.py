from .base import *  # noqa: F401, F403
from .base import env

DEBUG = True
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-not-for-production-use")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "web"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
