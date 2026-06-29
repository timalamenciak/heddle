# Reproducibility

## Environment

- Python: 3.12
- Production database: PostgreSQL 16
- Container base: digest-pinned in `Dockerfile`
- Python environments: hash-locked in `requirements.txt` and
  `requirements-dev.txt`
- Schema changes: ordered Django migrations in each app

Regenerate locks after editing the `.in` files:

```bash
uv pip compile requirements.in --generate-hashes --python-version 3.12 --universal -o requirements.txt
uv pip compile requirements-dev.in --generate-hashes --python-version 3.12 --universal -o requirements-dev.txt
```

## Data and provenance

Heddle does not ship a research dataset. Operators version their input datasets
outside the repository. Each import stores its source label, original filename,
row count, actor, timestamp, and SHA-256; raw CSV data is deleted after success.
External responses are cached with source-specific records/logs and proposed
changes remain attributable.

KGX, badge, and invite ZIP outputs contain a manifest or metadata document with
the Heddle version and slice information. Reproducing an exact output requires:

1. the same database snapshot;
2. the same Heddle commit/version and locked environment;
3. the same segment/event identifiers and consent/quality state;
4. a recorded export audit event.

The application contains no stochastic algorithms, so random seeds are not
applicable. Timestamps, user attribution, and external service responses are
expected sources of byte-level variation.
