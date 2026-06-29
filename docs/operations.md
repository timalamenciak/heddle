# Operations

Use the deployment checklist before every release. Production runs the
digest-pinned Docker image behind a TLS reverse proxy with PostgreSQL on an
internal network.

## Release procedure

1. Review `CHANGELOG.md` and bump `config/version.py`.
2. Run the complete CI matrix and a PostgreSQL-backed smoke test.
3. Back up and restore a staging database.
4. Apply migrations in staging, then run `manage.py check --deploy`.
5. Tag the reviewed commit and build the image from that tag.
6. Retain the image digest, database backup identifier, and CI run with release
   notes.

## Backup and recovery

Back up PostgreSQL at least daily, encrypt backups, restrict access, and test a
restore quarterly. A restore drill is incomplete until login, record counts,
audit history, import history, and a representative KGX export are verified.

## Logging and monitoring

Application errors are written to standard output for platform collection.
Forward audit/security logs to restricted append-only storage. Alert on repeated
authentication failures at the reverse proxy, HTTP 5xx spikes, failed backups,
and unavailable database health checks. Do not log CSV contents, passwords,
private notes, or full external records.

## Data retention

Raw CSV uploads are deleted immediately after successful application. Define
deployment-specific retention periods for failed/unapplied imports, cached
external records, exports, audit events, backups, and dormant accounts based on
the applicable consent and institutional policies.
