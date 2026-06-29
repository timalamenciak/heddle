FROM python:3.14.6-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9

WORKDIR /app

# Create non-root user before installing anything
RUN groupadd --system heddle && useradd --system --gid heddle heddle

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .

# Collect static assets (placeholder creds; no DB touched during collectstatic)
RUN SECRET_KEY=collectstatic-placeholder \
    DATABASE_URL=postgres://x:x@localhost/x \
    ALLOWED_HOSTS=localhost \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    python manage.py collectstatic --noinput

# Runtime as non-root
USER heddle

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "60"]
