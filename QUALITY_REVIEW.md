# Heddle quality-control review

Review date: 2026-06-27  
Checklist: `QUALITY_CHECKLIST.md` supplied by the project owner  
Scope: `dev_shared/heddle` after the remediation pass documented in
`QC_REMEDIATION_PLAN.md`

Statuses are based on repository or command evidence. Missing external evidence
is not inferred.

## 1. JOSS review

| ID | Status | Evidence and comments | Recommendation if not PASS |
|---|---|---|---|
| JOSS-01 | PASS | `README.md` states the research-infrastructure purpose and metadata-quality problem. | — |
| JOSS-02 | PASS | `README.md` identifies research data managers, organizers, and EcoWeaver contributors. | — |
| JOSS-03 | PASS | `README.md` and `AGENTS.md` explain EcoWeaver, CAMO/ELMO, KGX, provenance, and research context. | — |
| JOSS-04 | PASS | `README.md` distinguishes Heddle from EcoWeaver, rosettaR, ORCID, Crossref, OpenAlex, Wikidata, and ROR. | — |
| JOSS-05 | PASS | `README.md` exists. | — |
| JOSS-06 | PASS | Docker and local hash-locked installation instructions are present. | — |
| JOSS-07 | PASS | `README.md` contains a Docker quick start. | — |
| JOSS-08 | PASS | `docs/workflows/` documents import, metadata, event, invite, badge, and KGX workflows. | — |
| JOSS-09 | PASS | `README.md` documents management-command discovery; command implementations include Django help. | — |
| JOSS-10 | PASS | `README.md` and workflow docs define CSV, ZIP, manifest, badge, and KGX formats. | — |
| JOSS-11 | PASS | `.in` dependency intent and complete hash-locked `.txt` environments are documented. | — |
| JOSS-12 | PASS | `docs/limitations.md` documents tenancy, external-data, scaling, audit, testing, and accessibility limits. | — |
| JOSS-13 | WARNING | `README.md` gives an interim version/commit citation procedure, but formal metadata is absent. | Approve author metadata and add `CITATION.cff`. |
| JOSS-14 | WARNING | Dependency resolution, tests, production checks, and static collection succeed. Docker image build was attempted but the local Docker daemon was unavailable. | Let the new Linux CI run the clean install and image build. |
| JOSS-15 | PASS | `requirements*.txt` pin all transitive versions with hashes; Docker base is digest-pinned. | — |
| JOSS-16 | WARNING | `.github/workflows/ci.yml` installs locked dependencies and builds the image, but no CI run exists because this directory has no Git repository. | Initialize Git and require passing CI. |
| JOSS-17 | PASS | `LICENSE` contains the standard MIT License grant and conditions. | — |
| JOSS-18 | PASS | `LICENSE` states `Copyright (c) 2026 Heddle contributors`. | — |
| JOSS-19 | PASS | Automated unit, view, integration, security-regression, and end-to-end tests exist. | — |
| JOSS-20 | PASS | `546 passed`; coverage gate passed at 91.45%. | — |
| JOSS-21 | PASS | Major import, metadata, RBAC, event, export, privacy, enrichment, and KGX behavior is covered; `tests/test_e2e.py` composes the workflow. | — |
| JOSS-22 | FAIL | No Git metadata or versioned release evidence. | Initialize/restore Git and publish a reviewed release. |
| JOSS-23 | FAIL | `CITATION.cff` is absent. | Add after authors approve their metadata. |
| JOSS-24 | FAIL | No authoritative authors list. | Confirm contributors/authors and record them in README/CITATION. |

JOSS totals: **18 PASS, 3 WARNING, 3 FAIL**.

## 2. NASA software assurance

| ID | Status | Evidence and comments | Recommendation if not PASS |
|---|---|---|---|
| NASA-REQ-01 | PASS | `docs/requirements.md` defines testable functional/security requirements. | — |
| NASA-REQ-02 | PASS | Requirements table maps each ID to implementation and verification. | — |
| NASA-REQ-03 | PASS | Assumptions are explicit in requirements, threat model, and limitations. | — |
| NASA-VV-01 | PASS | Extensive unit tests across all apps. | — |
| NASA-VV-02 | PASS | View/service/database integration tests exercise app boundaries. | — |
| NASA-VV-03 | PASS | Security and bug fixes include regression tests. | — |
| NASA-VV-04 | PASS | `tests/test_e2e.py` plus authenticated browser smoke test. | — |
| NASA-VV-05 | WARNING | KGX validation and expected fixtures pass, but no independent rosettaR round-trip or external scientific validation artifact exists. | Add a checked rosettaR round-trip fixture with expected graph results. |
| NASA-VV-06 | PASS | Tests cover malformed identifiers, unsafe URLs, formula injection, consent, critical issues, duplicate imports, size limits, and roles. | — |
| NASA-VV-07 | PASS | Invalid input and failure paths are tested; internal exceptions are logged but not disclosed. | — |
| NASA-CODE-01 | PASS | Ruff is configured and clean. | — |
| NASA-CODE-02 | PASS | Ruff security rules, Bandit, mypy, Vulture, Django deploy checks, and dependency audit were run. | — |
| NASA-CODE-03 | PASS | Mypy passes with Django stubs. | — |
| NASA-CODE-04 | PASS | Ruff formatting/lint rules and contribution instructions define standards. | — |
| NASA-CODE-05 | PASS | Vulture at 90% confidence reports no non-migration dead code. | — |
| NASA-CODE-06 | PASS | Ruff enforces McCabe complexity <=20; schema assembly/filter functions are the documented higher-complexity paths. | — |
| NASA-CM-01 | FAIL | `dev_shared/heddle` has no `.git` directory. | Initialize or restore the repository before further shared development. |
| NASA-CM-02 | FAIL | No tags can exist without Git history. | Tag reviewed releases after repository setup. |
| NASA-CM-03 | PASS | Runtime and development dependencies are transitively pinned with hashes. | — |
| NASA-CM-04 | PASS | `CHANGELOG.md` exists and records this pass. | — |
| NASA-CM-05 | PASS | Digest-pinned Docker base, hash locks, migrations, and reproducibility docs exist. | — |
| NASA-CR-01 | FAIL | No pull-request/review history is available. | Require a second reviewer for security-sensitive PRs. |
| NASA-CR-02 | PASS | `CHANGELOG.md` and remediation plan document significant changes. | — |
| NASA-CR-03 | N/A | No reviewer-comment system/history exists in the supplied directory. | Address comments through PR review after Git setup. |
| NASA-CI-01 | PASS | `.github/workflows/ci.yml` is configured with least-privilege permissions and SHA-pinned actions. | — |
| NASA-CI-02 | PASS | CI runs lint, types, coverage tests, migration/deploy checks, static checks, audits, and image build. | — |
| NASA-CI-03 | WARNING | Local code/test/static/Compose checks pass; Docker build is unverified because the daemon is stopped; remote CI has not run. | Run CI and a PostgreSQL-backed image smoke test. |
| NASA-CI-04 | N/A | Automated releases are not appropriate until ownership/license/version-control gaps close. | Add a signed release workflow later. |
| NASA-SEC-01 | WARNING | `.env` matches the example placeholders and is ignored; Detect-Secrets found only documented development/test credentials. No Git history exists to prove secrets were never committed. | Create Git history from a clean secret scan and add secret scanning to the host platform. |
| NASA-SEC-02 | PASS | `pip-audit -r requirements.txt`: no known vulnerabilities; Dependabot configured. | — |
| NASA-SEC-03 | PASS | Bounded CSV validation, model/form checks, safe redirects, ORM usage, CSP, allowlisted outbound HTTP, and database constraints are implemented and tested. | — |
| NASA-SEC-04 | PASS | Consent filters, export exclusions, private-note controls, PII cleanup, generic errors, and audit metadata minimization are implemented. | — |
| NASA-REL-01 | PASS | Console application/error logging is configured; sensitive values are excluded by policy. | — |
| NASA-REL-02 | PASS | Domain validation errors and meaningful user messages replace raw exception disclosure. | — |
| NASA-REL-03 | PASS | Duplicate apply, invalid import, external failure, and invalid suggestion paths recover safely. | — |
| NASA-REL-04 | PASS | Context managers close HTTP/ZIP resources; transactions roll back imports; raw uploaded PII is erased after success. | — |

NASA totals: **28 PASS, 3 WARNING, 3 FAIL, 2 N/A**.

## 3. RAISE AI assurance

Heddle does not use AI or LLMs. ORCID/Crossref/OpenAlex/Wikidata integrations are
deterministic metadata lookups whose outputs require human acceptance. Therefore
all RAISE items are **N/A**:

- RAISE-R-01 through RAISE-R-04: N/A — no AI purpose/use cases.
- RAISE-A-01 through RAISE-A-04: N/A — no models or prompts.
- RAISE-I-01 through RAISE-I-04: N/A — no AI prompts/parameters/confidence outputs.
- RAISE-S-01 through RAISE-S-04: N/A — no AI failure mode; external-metadata risks are covered in `docs/limitations.md`.
- RAISE-E-01 through RAISE-E-04: N/A — no AI-generated content.

RAISE totals: **0 PASS, 0 WARNING, 0 FAIL, 20 N/A**.

## 4. Research reproducibility

| ID | Status | Evidence and comments | Recommendation if not PASS |
|---|---|---|---|
| REP-01 | PASS | Hash-locked environments, digest-pinned base, migrations, and `docs/reproducibility.md`. | — |
| REP-02 | N/A | No stochastic algorithms are used. | — |
| REP-03 | N/A | Heddle ships no research input dataset; operator dataset-version responsibility is documented. | If publishing a study, archive its input snapshot separately. |
| REP-04 | WARNING | Reproduction procedure is documented, but no frozen example database/output bundle demonstrates byte/semantic reproduction. | Add a small de-identified fixture dataset and expected exports. |
| REP-05 | PASS | `tests/test_e2e.py` runs import through validated graph/export outputs end to end. | — |
| REP-06 | PASS | KGX/badge/invite ZIP metadata includes `heddle_version`; people export responses identify it in a header. | — |
| REP-07 | PASS | Import fingerprints/source/actor, external logs/suggestions, export manifests, and audit events retain provenance. | — |

Reproducibility totals: **4 PASS, 1 WARNING, 0 FAIL, 2 N/A**.

## Verification record

- Tests: `546 passed`, 91.45% coverage, 90% gate satisfied.
- Lint/types: Ruff and mypy pass.
- Static analysis: Bandit zero findings; Vulture zero high-confidence non-migration findings.
- Dependencies: pip-audit reports no known vulnerabilities.
- Django: deploy check passes with explicit strong test settings; no migration drift.
- Assets: production `collectstatic` succeeds; local HTMX/Tailwind checksums verify.
- Compose: `docker compose config --quiet` passes.
- Browser: login, authorization-aware navigation, invalid/valid ORCID validation,
  record creation, local assets, and zero browser console warnings/errors verified.
- Docker image: **not built locally** because the Docker daemon is unavailable.

## Overall assessment and major risks

The implemented application is materially more secure and has strong automated
correctness evidence. It is suitable for controlled single-organization staging,
but it is not publication-ready and should not yet be treated as a hardened
multi-team production service.

Major remaining risks:

1. No complete authors list, citation file, Git history, reviewed release, or
   executed CI record.
2. Authorization is a global single-organization role model. Apart from import
   ownership, there is no record/organization-level access boundary; all
   Organizer users can export eligible deployment-wide records.
3. Application-layer authentication throttling is absent and must be enforced at
   the reverse proxy.
4. Audit rows are admin-read-only but not cryptographically or externally
   immutable against a database administrator.
5. Docker/Linux and PostgreSQL concurrency/backup-restore acceptance remain
   unproven on this workstation.

Publication readiness: **Significant revisions required**.

## Priority recommendations

### High

- Approve authors/citation; initialize Git; enable reviewed PRs and CI; create a
  signed/versioned release.
- Decide and document whether global roles meet the data-governance model. Add
  tenant/record permissions before any multi-team deployment.
- Run the configured Linux image build and PostgreSQL staging acceptance suite;
  configure TLS, reverse-proxy throttling, backups, and external audit retention.

### Medium

- Add a de-identified reproducibility fixture and independent rosettaR round trip.
- Add retention automation for abandoned imports and streaming for large exports.
- Commission an accessibility review and property/fuzz tests for parsers.

### Low

- Expand management-command coverage and prepare the Django 6 transition.

**Reviewer declaration:** Every checklist item was explicitly assessed from
repository and command evidence. Items without evidence were not marked PASS.
