# Threat model — heddle

## Assets

| Asset | Sensitivity | Notes |
|-------|-------------|-------|
| Person records (email, ORCID, affiliation) | High | PII; drives invite lists |
| Organization records | Medium | Mostly public info |
| Expertise and event participation | Medium | Can reveal research direction |
| Audit logs | High | Record of who changed what |
| User credentials | Critical | Control platform access |
| Export CSVs | High | May contain PII |

## Trust boundary

```
Internet → [Reverse proxy / TLS termination] → Django (web container) → PostgreSQL
```

Administrators access Django admin over HTTPS. No public-facing API in Phase 0.

## Threat actors

| Actor | Capability | Scenario |
|-------|-----------|----------|
| Unauthenticated internet user | Low | Enumeration, login brute-force |
| Authenticated Viewer | Low | Access data beyond their view permissions |
| Authenticated Organizer | Medium | Exfiltrate segment/invite data |
| Compromised Admin account | High | Exfiltrate all records, demote users |
| Insider (Superadmin) | Full | Covered by audit log |
| Dependency supply chain | Medium | Malicious package in requirements.txt |

## Key mitigations

### Authentication & authorisation
- All views require login (`LoginRequiredMixin`). Role checked at dispatch via `RoleRequiredMixin`.
- Django admin restricted to `is_staff` users (Admin + Superadmin roles only).
- Superadmin is the only role that can delete users or set the superadmin role.
- Password reset uses Django's built-in HMAC token; tokens expire after 1 hour by default.
- Login and password-reset throttling is required at the production reverse proxy.

### Data exposure
- `notes_private` never exported unless admin explicitly opts in (Phase 1+).
- Email never in graph or public exports (Phase 6).
- Non-consenting people excluded from invite lists and public exports by default (Phase 3+).

### Injection
- Django ORM used throughout; raw SQL only if parameterised.
- CSV exports escape leading `= + - @ \t` characters (Phase 1).
- Template auto-escaping enabled (Django default).
- CSRF protection on all state-changing requests.
- Same-origin redirect validation prevents post-action open redirects.
- A restrictive Content Security Policy permits scripts and styles from Heddle only.

### Transport
- HTTPS enforced via `SECURE_SSL_REDIRECT` or reverse-proxy.
- HSTS with 1-year max-age prevents downgrade attacks.
- Secure, HttpOnly cookies in production.

### Infrastructure
- Docker image runs as non-root (`heddle` user).
- PostgreSQL not exposed on public interface in production.
- All secrets via environment variables.
- Outbound API traffic is restricted to approved HTTPS hosts with time and size limits.
- Import sessions are scoped to their creator (Admin+ may investigate all sessions).

## Out of scope (Phase 0)

- ORCID OAuth token handling (Phase 4 — tokens never stored)
- External API integrations (Phases 4–6)
- Multi-tenant isolation (single organisation per deployment)
- DDoS / rate-limiting (handle at reverse-proxy layer)
