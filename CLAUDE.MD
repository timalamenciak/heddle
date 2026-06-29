# CLAUDE.md — heddle

## What this is
heddle is the engagement CRM and metadata-quality platform for the EcoWeaver project.
It is the **source of truth** for people, organizations, affiliations, expertise,
events, participation, publications, and collaborations across workshops, hackathons,
conferences, and international collaborations.

Its job is to keep that metadata **trustworthy and provenance-tracked**, and to export
clean datasets into:
- the EcoWeaver knowledge graph (via KGX → rosettaR)
- downstream artifact tools (e.g. a separate badge/DXF generator)
- reporting and invite lists

heddle does NOT generate badges, DXF, or QR artifacts. It exports clean, verified data;
a separate tool consumes it.

## Design philosophy: metadata is a first-class workflow
Every record must be able to answer:
- Where did this data come from? (`source`)
- When was it last checked / verified? (`metadata_last_checked_at`, `metadata_last_verified_at`)
- Who verified it? (`verified_by`)
- What looks suspicious? (open MetadataIssues)
- What should be fixed next? (suggested_fix)
- Can we safely use it in an invite list or public export? (quality score + no critical issues)

Most CRMs let you store records but not keep them trustworthy. That trustworthiness is
the product. When in doubt, favour the design that makes provenance and verification
visible over the one that's faster to enter.

## EcoWeaver context (domain the agent should assume)
- EcoWeaver is an open knowledge graph linking causal ecological evidence to restoration
  practice, built on the Causal Mosaic Ontology (CAMO), a LinkML schema.
- Related tooling already in use: ELMO (Ecolink Model Ontology), rosettaR (R package for
  KGX/Rosetta statement conversion), the oboizer Python suite for OBO curation.
- Graph exchange format is **KGX** (Biolink-aligned). Graph exports MUST target KGX so
  they round-trip through rosettaR. Define export schemas in LinkML and validate against them.
- Expertise vocabularies of interest include: ENVO, PATO, RO, CAMO, ELMO, OpenAlex
  concepts, Wikidata, GBIF, plus local terms.
- Events are real: international workshops, hackathons (EcoTransform-style), and
  conferences (OERC-style). Partnerships include Ducks Unlimited Canada.

## Stack (v1)
- Django (current stable, 5.x) + Django templates + HTMX
- PostgreSQL
- Tailwind (pick one CSS system; do not mix)
- Docker Compose (web + db only in v1)
- pytest, ruff, mypy (where practical)
- Nightly jobs = Django management commands run by cron/systemd timer

## Do NOT use (v1)
React • microservices • Kubernetes • a graph database • external AI/enrichment APIs •
Celery/Redis/beat • badge/DXF generation • ORCID OAuth or token storage.
(Several are fine in *later* phases when justified — see BUILD_PLAN.md. Don't add them early.)

## Architecture — apps
- `accounts`   — auth, roles (Superadmin/Admin/Organizer/Contributor/Viewer), RBAC, object perms
- `core`       — Person, Organization, Affiliation, ExpertiseTerm, PersonExpertise
- `events`     — Event, Participation, Session
- `metadata`   — MetadataCheck/Issue/Verification/FreshnessRule, quality scoring, dashboard
- `importer`   — CSV import: map → normalize → dry-run preview → upsert
- `exporter`   — people/roster/segment/badge-input CSV + export manifests
- `graph`      — KGX (and JSON-LD) exports; LinkML-validated
- `audit`      — audit log for sensitive actions
Publications/collaborations live in `core` and arrive in a later phase — do not stub them early.

## Invariants (never violate)
- All non-public views require login. RBAC + object-level permissions enforced.
- DEBUG=false, ALLOWED_HOSTS set, SECURE_SSL_REDIRECT configurable, secure cookies in prod.
- All secrets via env vars. No secrets in source. Never log ORCID data tied to a token.
- **Every export is CSV-formula-injection safe** (escape cells starting with = + - @ tab).
- Exports respect the requesting user's view permissions. Email never on public pages or
  in graph/public exports by default. `notes_private` never exported unless an admin
  explicitly selects it.
- **Derived data never overwrites human-entered data.** ORCID/import findings become
  MetadataSuggestions to accept/reject, not silent writes.
- Records flagged with **critical** metadata issues are excluded from invite lists and
  clean rosters by default.
- Docker image runs as non-root. Dependencies pinned.

## Conventions
- UUID primary keys everywhere.
- Any derived/imported field carries `source` and (where applicable) `confidence_score`.
- `metadata_status` ∈ {unreviewed, needs_review, verified, stale, conflicting, incomplete}.
- Metadata language is non-shaming: "Needs review", never "bad"/"missing"/"incomplete you".
- Quality-score weights live in the DB (a tunable rubric), and the score is always shown
  with a "why this score" breakdown — never an opaque number.
- New behaviour ships with tests. Lint and types must pass.
- Migrations are reviewed, named, and never auto-squashed without intent.

## How to work
- Run `make test` and `make lint` before declaring a step done.
- Imports are dry-run by default; show a preview/diff before applying.
- **Build only the current phase.** Do not scaffold future-phase models "to save time."
  If a future need is obvious, leave a `# TODO(phase-N)` and move on.
- When unsure about a domain term (CAMO, KGX, rosettaR, OERC), ask rather than guess.

## Definition of done (per phase)
A phase is done when: its acceptance tests pass, `make lint` is clean, the happy-path
flow works through the UI, docs for that phase exist, and no invariant above is broken.