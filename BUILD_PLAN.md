Phase 0 — Scaffold & guardrails

Goal: an empty-but-correct app you can log into, with the security/test rails in place.

Build: repo + CLAUDE.md; Django project (config/ + the 8 apps); Dockerfile (slim,
non-root) + docker-compose.yml (web + db); .env.example; Makefile
(up/down/migrate/createsuperuser/test/lint/shell/backup-db/restore-db); /healthz/;
pytest + ruff + mypy wired; accounts with the five roles, RBAC groups, user-admin UI,
password reset; audit log skeleton; SECURITY.md, docs/threat_model.md,
docs/deployment_security_checklist.md.

Done when: docker compose up --build runs; make test green; anonymous users get
redirected from protected views; a Viewer cannot edit; an Admin can manage users;
python manage.py check --deploy passes with documented exceptions.

Phase 1 — Core CRM vertical slice

Goal: import people, see/edit them, export them clean. One path, end to end.

Build: Person, Organization, Affiliation, minimal ExpertiseTerm/PersonExpertise;
list + detail + edit UI with HTMX; list filters (country, continent, organization,
missing ORCID, consent_contact, metadata_status). Simple people CSV import in
importer: column mapping → normalization (ORCID, DOI, email, country→continent,
whitespace, swapped given/family detection) → dry-run preview → upsert on
ORCID→email→normalized(name+org). Formula-injection-safe people CSV export with column
selection and UTF-8 BOM option.

Done when: you import a sample CSV, the preview shows creates vs updates vs matches,
applying it populates records, you edit one, and you export a clean CSV.
Tests: normalization, duplicate detection, export escaping, dry-run makes no writes.

Phase 2 — Metadata quality engine

Goal: the differentiator — trustworthiness as a workflow.

Build: metadata app with MetadataCheck, MetadataIssue, MetadataVerification,
MetadataFreshnessRule. Person + Organization checks from the original (missing/invalid
ORCID, unverified ORCID, stale sync, missing country/continent/org/consent, duplicates by
ORCID/email/normalized-name, stale affiliation, no expertise, no linked activity,
profile not updated in 365d; org: missing country/website/ROR, dup, stale, no people).
Quality score 0–100 from DB-stored weights, always shown with a breakdown. Metadata
Quality Dashboard + per-record issues panel + one-click verify/ignore/resolve + "run
checks now". Nightly checks via manage.py run_metadata_checks.

Done when: each check produces its expected issues; resolved issues don't reappear
unless data changes; ignored stay ignored; the score changes after a fix and the
breakdown explains it; "why is this flagged?" is visible on each issue.

Phase 3 — Events, participation, segments, invite lists

Goal: the core organizer job — turn clean data into a defensible invite list.

Build: Event, Participation, minimal Session; event dashboard + roster + bulk
status updates. SavedSegment with a visual filter builder (country/continent/org/
org-type/expertise/free-text/prior participation/event role/consent flags/ORCID
verified/synced-within-N-days/quality status/no critical issues/not-already-invited).
Preview table with "why matched". Invite-list CSV export that excludes critical-issue
and non-consented records by default, with the manifest noting exclusions.

Done when: you create an event, build a "Europe + (restoration OR AI OR knowledge
graph) + consent_contact + no critical issues + not already invited" segment, see why
each person matched, and export an invite list whose excluded rows are explained in the
manifest.

Phase 4 — ORCID verification (public API, no tokens)

Goal: enrich and verify without ever overwriting.

Build: ORCID iD validation/normalization; public-record + public-works fetch (3.0 schema,
mocked in tests); ORCIDProfile, ORCIDWork, MetadataSuggestion. "Sync ORCID" button →
background-ish manage.py sync_orcid → suggestion preview → accept/reject (one + bulk
low-risk). Create publications from works (Phase 5 models permitting — otherwise stage
the raw works). Warn on name divergence, conflicting affiliations, newer remote works.
Mark fields verified-by-ORCID. No tokens stored or logged.

Done when: a mocked sync produces suggestions (not writes); accepting one updates the
field and records a MetadataVerification; conflicting data raises a warning issue; a
stale sync raises a freshness issue.

Phase 5 — Publications & collaborations

Build: Publication, Authorship, Collaboration; dedup by normalized DOI and by
normalized title+year; link authors to Person; infer coauthorship collaborations; publication


collaboration history on the Person page; related metadata checks (missing/invalid/dup
DOI, unlinked authors, unreviewed ORCID import, unverified-in-365d).


Done when: ORCID works import as publications, authors link, dups merge, coauthor
edges appear, and the new checks fire correctly.

Phase 6 — Graph & badge exports (EcoWeaver integration)

Goal: plug straight into the EcoWeaver pipeline and the badge tool.

Build: KGX export — nodes.tsv / edges.tsv with Biolink-aligned categories and
predicates where available, falling back to schema: and commons:. Define the
node/edge schema in LinkML; validate every export against it. JSON-LD optional.
badge_tool_input_csv (person_id, display_name, public_label, orcid, organization,
country, event_code, event_name, participation_role/status, consent_public_profile,
qr_target_url, metadata_quality_score, metadata_status) + export manifest. Privacy:
anonymize non-consenting people in public exports; never export email by default;
include metadata_status so downstream tools can filter. Slices: full / segment / event /
person-neighbourhood / org-neighbourhood / N-hop.

Done when: the KGX export validates against the LinkML schema and is ingestible by
rosettaR (or matches the KGX spec in a round-trip test); privacy rules hold; the badge
CSV + manifest generate; ORCID-URI edges are correct.

Phase 7 — Dashboard & polish

Build: organizer dashboard cards (people, verified/missing ORCID, consent, stale syncs,
open/critical issues, possible dups, upcoming events, saved segments, recent
imports/exports); empty states; breadcrumbs; accessible forms; tooltips; "why flagged?"
everywhere; docs/workflows/*.md; one end-to-end test covering the full original
workflow (import → normalize → dedup → ORCID sync → segment → invite → roster → badge
input → graph slice → audit).

Optional later phases (only when justified)


Async (Celery/Redis) — when an import or sync is genuinely long-running.
ORCID OAuth account-linking — only if members will self-claim records.
True import rollback — if replayable upserts prove insufficient.
External enrichment (Crossref/OpenAlex) — gated behind explicit review, never auto-apply.