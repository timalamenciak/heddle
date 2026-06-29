# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email **security@racoonlab.example** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept if available)
- Affected versions

We aim to acknowledge reports within **48 hours** and provide a remediation
timeline within **7 business days**.

## Supported versions

| Version | Supported |
|---------|-----------|
| main    | Yes       |

## Security controls (summary)

- All non-public views require authentication. RBAC enforced at view level.
- `DEBUG=False` in production. `ALLOWED_HOSTS` set via env var.
- HTTPS enforced via `SECURE_SSL_REDIRECT` (or reverse-proxy — see deployment checklist).
- HSTS enabled with 1-year max-age, `includeSubDomains`, and `preload`.
- Session and CSRF cookies are `Secure` and `HttpOnly` in production.
- `X-Frame-Options: DENY`. `X-Content-Type-Options: nosniff`.
- All secrets loaded from environment variables; none in source control.
- CSV exports are formula-injection safe (cells starting with `=`, `+`, `-`, `@`, tab escaped).
- Email addresses never appear in public pages or graph exports by default.
- Derived/imported data never silently overwrites human-entered data.
- Docker image runs as non-root user `heddle`.
- Dependencies are pinned in `requirements.txt`.
- Audit log records sensitive actions with user, IP, timestamp, and non-secret changed-field metadata.
- Browser-executable assets are served locally under a restrictive Content Security Policy.
- CSV uploads are size/row/column bounded, owner-scoped, and raw CSV PII is erased after apply.
- Outbound API requests are HTTPS-only, host-allowlisted, timed out, and response-size bounded.

Application logging and audit metadata deliberately omit passwords, CSV contents,
private-note values, and external API payloads. Operators should forward audit
events to append-only storage when tamper resistance is required.
