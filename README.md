# Heddle

Heddle is a self-hosted engagement manager made for the EcoWeaver project. 
It keeps provenance-tracked records of people, organizations, expertise, 
events, participation, publications, and
collaborations, then produces privacy-aware CSV and KGX exports for research
workflows.

The intended users are research data managers, workshop organizers, and
EcoWeaver contributors. Heddle addresses a scientific-infrastructure problem:
contact and collaboration metadata becomes stale, inconsistent, or
untraceable, which undermines reproducible network analysis and responsible
engagement. Unlike general-purpose CRMs, Heddle makes provenance, verification,
consent, and explainable quality scores part of the workflow.

This is mainly an internal tool, but putting here in case others want it.

## Quick start with Docker

Requirements: Docker Engine with Compose v2.

```bash
cp .env.example .env
# Replace SECRET_KEY with a random value for any non-throwaway environment.
docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Open `http://127.0.0.1:8000/`. The development Compose file binds the web and
database ports to localhost only.

## Local development

Heddle supports Python 3.12 and PostgreSQL 16. Tests use SQLite for speed.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows PowerShell
python -m pip install --require-hashes -r requirements-dev.txt
pytest
ruff check .
mypy .
```

On POSIX shells, activate with `source .venv/bin/activate`. Direct dependency
intent lives in `requirements.in` and `requirements-dev.in`; the corresponding
`.txt` files are complete hash-locked environments generated with `uv`.

## Core workflow

1. Create users and assign the least-privileged role needed.
2. Import a bounded UTF-8 or BOM-marked UTF-16 CSV and review its dry-run diff.
3. Apply the import; raw uploaded PII is erased after a successful apply.
4. Run metadata checks and review issues or external-data suggestions.
5. Build an event segment and export a consent-filtered invite list.
6. Export validated KGX or badge-tool input for downstream research tools.

See `docs/workflows/` for detailed examples.
Front-end asset provenance and rebuild instructions are in
`docs/frontend_assets.md`.

## Inputs and outputs

- Input: CSV contact/affiliation data; public ORCID, Crossref, OpenAlex, and
  Wikidata records fetched from fixed HTTPS hosts.
- Output: formula-injection-safe CSV, invite ZIPs with manifests, badge-tool
  CSV, and validated KGX `nodes.tsv`/`edges.tsv` ZIPs.
- Persistent data: PostgreSQL records plus append-oriented audit events.

Management commands include `run_metadata_checks`, `sync_orcid`,
`import_orcid_publications`, and the enrichment commands under
`enrichment/management/commands/`. Run `python manage.py help` for the complete
command list and `python manage.py help <command>` for arguments.

## Security and operations

Read `SECURITY.md`, `docs/threat_model.md`, `docs/deployment_security_checklist.md`,
and `docs/operations.md` before deployment. Production requires explicit strong
secrets, host allowlists, TLS, backups, and reverse-proxy rate limiting.

## Limitations

Heddle is single-organization software, not a multi-tenant service. External
metadata can be wrong and always requires human review. The SQLite test backend
does not replace PostgreSQL acceptance testing. See `docs/limitations.md`.

## Citation and license

Until a release archive and `CITATION.cff` are approved, cite the exact Heddle
version (`config/version.py`), repository commit, access date, and project title.
Heddle is released under the MIT License. Formal author metadata must still be
approved before JOSS submission.
