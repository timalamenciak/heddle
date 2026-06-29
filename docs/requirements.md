# Requirements and traceability

This is the minimum verified requirement set for Heddle 0.1.x. Each requirement
maps to implementation and automated evidence.

| ID | Requirement | Implementation | Verification |
|---|---|---|---|
| HED-AUTH-01 | Non-public views require authentication and the documented minimum role. | `accounts/mixins.py`, view classes | `accounts/tests/test_views.py`, per-app view tests |
| HED-PII-01 | Email and private notes are absent from graph/public exports by default. | `exporter/`, `graph/exporters/` | `exporter/tests/`, `graph/tests/` |
| HED-CONSENT-01 | Invite/badge exports exclude records lacking the relevant consent. | `events/services.py`, `graph/exporters/badge_csv.py` | `events/tests/test_invite_export.py`, `graph/tests/test_badge_csv.py` |
| HED-CSV-01 | CSV output neutralizes spreadsheet formulas. | `exporter/services.py`, `events/services.py`, `graph/exporters/` | export tests in each app |
| HED-IMPORT-01 | Imports are bounded, owner-scoped, previewed, and applied no more than once. | `importer/services.py`, `importer/views.py` | `importer/tests/test_views.py`, `test_importer.py` |
| HED-IMPORT-02 | Raw uploaded PII is erased after a successful import; its SHA-256 remains. | `ImportSession`, `ImportPreviewView.post` | `test_successful_apply_is_audited_and_erases_raw_csv` |
| HED-PROV-01 | Sensitive writes and exports retain actor, time, peer IP, object, and non-secret change metadata. | `audit/services.py`, audited views | audit and workflow tests |
| HED-EXT-01 | External findings never overwrite records without an organizer accepting a supported suggestion. | `enrichment/services.py`, `metadata/views.py` | `metadata/tests/test_suggestions.py`, `enrichment/tests/` |
| HED-NET-01 | Outbound application HTTP is HTTPS-only, host-allowlisted, timed out, and size-bounded. | `enrichment/adapters/http.py` | `enrichment/tests/test_http.py` |
| HED-EXPORT-01 | KGX exports validate against the checked-in schema and identify the Heddle version. | `graph/validators.py`, `graph/schema/`, exporters | `graph/tests/test_validators.py`, `test_kgx.py` |
| HED-OPS-01 | Production fails closed on weak secrets or empty host allowlists and passes Django deployment checks. | `config/settings/production.py` | CI deployment-check step |

## Assumptions

- One trusted organization operates each deployment; Heddle does not provide
  tenant isolation.
- TLS termination and login rate limiting are enforced by a correctly
  configured reverse proxy.
- Operators protect PostgreSQL, backups, and exported files as personal data.
- Organizers are authorized to view the records present in their deployment.
