#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/startup_hosting/.env.pc"
PYTHON="$ROOT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo 'Missing .venv. Create it and install requirements.txt first.' >&2
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  SECRET_KEY=$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(64))')
  MFA_KEY=$($PYTHON -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
  umask 077
  sed \
    -e "s|__SECRET_KEY__|$SECRET_KEY|" \
    -e "s|__MFA_KEY__|$MFA_KEY|" \
    "$ROOT_DIR/startup_hosting/env.pc.template" > "$ENV_FILE"
  echo "Created private environment: $ENV_FILE"
fi
set -a
. "$ENV_FILE"
set +a
cd "$ROOT_DIR"
$PYTHON manage.py migrate
$PYTHON manage.py collectstatic --noinput
if ! $PYTHON manage.py shell -c "from hirewise.models import User; raise SystemExit(0 if User.objects.filter(email__endswith='@demo.example.invalid').exists() else 1)"; then
  $PYTHON manage.py seed_demo
else
  echo 'Demo users already exist; existing credentials were not changed.'
fi
$PYTHON manage.py check
echo 'PC hosting setup complete.'
