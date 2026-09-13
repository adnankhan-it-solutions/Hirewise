#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMPOSE="docker compose --env-file $ROOT_DIR/startup_hosting/.env.hosting -f $ROOT_DIR/startup_hosting/compose.yaml"
$COMPOSE ps
$COMPOSE exec -T web python manage.py check --deploy
$COMPOSE exec -T web python manage.py makemigrations --check --dry-run
$COMPOSE exec -T web python manage.py test --verbosity 1
$COMPOSE exec -T web python -m ruff check .
curl -fsS "${PUBLIC_ORIGIN:-http://localhost:8080}/health/"
printf '\nStartup hosting verification passed. Browser smoke testing still requires a local browser environment.\n'
