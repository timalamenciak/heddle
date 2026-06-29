from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403
from .base import env

# Required in production — no defaults provided intentionally
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("Production SECRET_KEY must be random and at least 50 characters")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production ALLOWED_HOSTS must contain at least one hostname")

DEBUG = False

# HTTPS / security headers
# If running behind a TLS-terminating reverse proxy (nginx, load balancer),
# set USE_SECURE_PROXY_SSL_HEADER=True and SECURE_SSL_REDIRECT=False in env.
# That proxy must set the X-Forwarded-Proto header.
# Exception documented: SECURE_SSL_REDIRECT may be False behind a proxy —
# the proxy enforces HTTPS before requests reach Django.
_behind_proxy = env.bool("USE_SECURE_PROXY_SSL_HEADER", default=False)
if _behind_proxy:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = False  # proxy handles redirect
else:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

X_FRAME_OPTIONS = "DENY"
