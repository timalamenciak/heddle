# Limitations and failure modes

- Heddle is single-organization software. Roles are global and are not tenant
  boundaries or per-record sharing rules.
- External services can be unavailable, rate-limit requests, or return wrong or
  biased metadata. Results are suggestions, not truth; a human must review them.
- Name/email/ORCID deduplication can produce false matches. The import preview
  is the control that prevents silent changes.
- SQLite is used for automated tests; production acceptance must also exercise
  PostgreSQL migrations, backups, restore, and concurrency.
- Application memory still scales with an accepted CSV or generated export,
  though CSV input is capped. Very large deployments need streaming exports.
- Heddle does not implement application-layer login throttling. The production
  reverse proxy must rate-limit login and password-reset endpoints.
- Audit records are protected against editing in the admin interface, but a
  database administrator can alter them. High-assurance deployments should
  forward logs to append-only external storage.
- No public API stability guarantee exists before 1.0.
- Accessibility has not received an independent WCAG audit.

Common recoverable failures (external API timeout, invalid CSV, duplicate import
apply, invalid suggestion) are surfaced without exposing internal exception
details. Database and infrastructure failures require operator recovery from
tested backups.
