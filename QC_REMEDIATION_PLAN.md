# QC remediation plan

Review date: 2026-06-27

## Completed in this hardening pass

- Added bounded, structurally validated CSV ingestion; UTF-8 and BOM-marked
  UTF-16 support; creator-only session access; transaction locking; one-time
  apply; retained SHA-256 provenance; and post-apply raw-PII deletion.
- Removed executable CDN dependencies, vendored HTMX, compiled Tailwind, added
  asset checksums, and enforced a restrictive CSP and browser security policy.
- Added safe same-origin redirects, real ORCID check-digit validation, outbound
  HTTPS host allowlisting, redirect validation, response size caps, safer error
  messages, and production fail-closed settings.
- Added audit events for sensitive changes, metadata decisions, enrichment,
  imports, and exports without copying sensitive values into audit metadata.
- Added database integrity constraints for targets, scores, confidence, dates,
  and collaboration endpoints.
- Fixed all mypy errors, enabled complexity checks, confirmed high-confidence
  dead-code scanning, and added security-focused regression tests.
- Added hash-locked dependencies, a digest-pinned container base, CI quality and
  security gates, Dependabot, a 90% coverage gate, versioned export metadata,
  README/workflow/requirements/reproducibility/limitations/operations docs, and
  a changelog.

## Requires owner or deployment action

1. Confirm the complete author list and citation metadata, then add
   `CITATION.cff`. The MIT license and copyright statement are now present.
2. Initialize or restore Git history, configure a remote, require reviewed pull
   requests and passing CI, then create a signed/versioned release.
3. Decide whether global single-organization roles are sufficient. If multiple
   teams or restricted record sets will coexist, design and test real
   organization/record-level permissions before deployment.
4. Run the configured CI on Linux with a live Docker daemon and complete a
   PostgreSQL-backed migration/concurrency/backup-restore acceptance test.
5. Configure TLS, reverse-proxy authentication rate limits, centralized error
   logging, and append-only external audit retention.

## Later improvements

- Add streaming exports for very large datasets and an automated retention job
  for abandoned/failed import sessions.
- Add property/fuzz tests for CSV and identifier parsers, an independent
  rosettaR/KGX round-trip fixture, and an accessibility audit.
- Expand management-command tests and remove the Django 5.2 transitional URL
  setting during the Django 6 upgrade.
