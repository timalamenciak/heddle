.PHONY: up down migrate makemigrations createsuperuser test lint shell backup-db restore-db security check-deploy

# ── Docker Compose ────────────────────────────────────────────────────────────

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

createsuperuser:
	docker compose exec web python manage.py createsuperuser

shell:
	docker compose exec web python manage.py shell

backup-db:
	docker compose exec db pg_dump -U heddle heddle > backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db:
	@test -n "$(BACKUP_FILE)" || (echo "Usage: make restore-db BACKUP_FILE=backup_xxx.sql" && exit 1)
	docker compose exec -T db psql -U heddle heddle < $(BACKUP_FILE)

# ── Local (no Docker required) ────────────────────────────────────────────────

test:
	pytest --cov=. --cov-report=term-missing --cov-fail-under=90

lint:
	ruff check .
	mypy .

lint-fix:
	ruff check --fix .

check-deploy:
	python manage.py check --deploy --settings=config.settings.production

security:
	pip-audit -r requirements.txt
	bandit -r accounts audit config core enrichment events exporter graph importer metadata -x '*/migrations/*,*/tests/*'
