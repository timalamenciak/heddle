# Changelog

All notable changes are documented here. This project follows Semantic
Versioning once public releases begin.

## Unreleased

### Security

- Bound and validate CSV uploads; isolate import sessions by owner.
- Make import application transaction-locked and one-time; erase raw CSV PII
  after success while retaining a SHA-256 fingerprint.
- Vendor front-end assets and apply a restrictive Content Security Policy.
- Allowlist outbound HTTPS API hosts and cap JSON response size.
- Validate redirect targets and ORCID check digits.
- Add audit events for sensitive mutations and exports.

### Quality

- Add database integrity constraints, a 90% coverage gate, CI security checks,
  hashed dependency locks, and versioned export manifests.
- Add the MIT License.
