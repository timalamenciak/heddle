# Deployment security checklist

Run through this before every production deployment.

## Environment configuration

- [ ] `SECRET_KEY` is a 50+ character random string, not the dev default
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` is set to the production domain(s) only
- [ ] `DATABASE_URL` points to the production database with a dedicated user and strong password
- [ ] `EMAIL_HOST_PASSWORD` is set and not logged
- [ ] No `.env` file is present on the production host (use real env vars or a secrets manager)

## TLS / HTTPS

- [ ] TLS certificate is valid and auto-renewing
- [ ] `SECURE_SSL_REDIRECT=True` **or** `USE_SECURE_PROXY_SSL_HEADER=True` (proxy handles redirect)
  - If using the proxy header option, verify the proxy strips `X-Forwarded-Proto` from untrusted clients
- [ ] HSTS header is served: `max-age=31536000; includeSubDomains; preload`
- [ ] Site submitted to HSTS preload list (after confirming HTTPS works)

## Django security check

Run and resolve all warnings:

```bash
python manage.py check --deploy --settings=config.settings.production
```

**Known documented exceptions:**
- `SECURE_SSL_REDIRECT` may be `False` when a reverse proxy enforces HTTPS
  and `SECURE_PROXY_SSL_HEADER` is correctly configured.

## Cookies & sessions

- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] `SESSION_COOKIE_HTTPONLY=True`
- [ ] `CSRF_COOKIE_HTTPONLY=True`
- [ ] Session timeout configured appropriately (`SESSION_COOKIE_AGE`)
- [ ] Reverse proxy rate-limits `/accounts/login/` and password-reset endpoints

## Database

- [ ] PostgreSQL user has minimal privileges (SELECT/INSERT/UPDATE/DELETE on app tables; no SUPERUSER)
- [ ] PostgreSQL not exposed on `0.0.0.0`; bound to `127.0.0.1` or Docker internal network only
- [ ] Automated backups configured and tested

## Docker / infrastructure

- [ ] Container runs as non-root user `heddle`
- [ ] Image built from the digest-pinned base image in `Dockerfile`
- [ ] Dependencies pinned in `requirements.txt`; no `--upgrade` in build
- [ ] `docker compose` does not expose the DB port publicly in production
- [ ] Log aggregation captures Django application logs
- [ ] Audit events are forwarded to access-restricted append-only storage where required

## Access control

- [ ] At least one Superadmin account exists with a strong password
- [ ] Default `admin` / `admin` credentials do not exist
- [ ] Admin site URL is at `/admin/` (consider moving in high-risk deployments)
- [ ] Password reset email backend is configured to a real SMTP server

## Post-deployment verification

```bash
# Confirm check passes
python manage.py check --deploy

# Confirm migrations are applied
python manage.py showmigrations

# Confirm static files collected
python manage.py collectstatic --dry-run
```

- [ ] Login works at `https://<domain>/accounts/login/`
- [ ] Anonymous request to `/` redirects to login
- [ ] Health check responds: `curl https://<domain>/healthz/` → `{"status":"ok"}`
- [ ] Admin access blocked for Viewer and Contributor accounts
