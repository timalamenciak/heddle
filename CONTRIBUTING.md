# Contributing

Use a feature branch and a pull request. Significant changes should update the
changelog, requirements traceability, tests, and relevant workflow docs.

Before requesting review, run:

```bash
ruff check .
mypy .
pytest --cov=. --cov-fail-under=90
python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

Security-sensitive changes require a second reviewer. Never commit `.env`,
production data, credentials, database dumps, or exports containing personal
information. Report vulnerabilities through the private process in
`SECURITY.md`.
