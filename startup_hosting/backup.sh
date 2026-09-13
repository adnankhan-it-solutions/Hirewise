#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/startup_hosting/.env.hosting"
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi
set -a
. "$ENV_FILE"
set +a
if [ -z "${BACKUP_PASSPHRASE:-}" ] || [ "$BACKUP_PASSPHRASE" = "CHANGE_ME_LONG_BACKUP_PASSPHRASE" ]; then
  echo 'Set a strong BACKUP_PASSPHRASE first.' >&2
  exit 1
fi
BACKUP_DIR="$ROOT_DIR/startup_hosting/backups"
mkdir -p "$BACKUP_DIR"
umask 077
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
COMPOSE="docker compose --env-file $ENV_FILE -f $ROOT_DIR/startup_hosting/compose.yaml"
$COMPOSE exec -T database pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE -out "$BACKUP_DIR/database-$STAMP.dump.enc"
sha256sum "$BACKUP_DIR/database-$STAMP.dump.enc" > "$BACKUP_DIR/database-$STAMP.dump.enc.sha256"
echo "Encrypted database archive created in $BACKUP_DIR. Copy it to separate restricted storage."
