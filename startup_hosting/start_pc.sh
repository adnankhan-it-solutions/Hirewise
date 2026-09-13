#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/startup_hosting/.env.pc"
RUNTIME_DIR="$ROOT_DIR/startup_hosting/runtime"
PID_FILE="$RUNTIME_DIR/hirewise.pid"
LOG_FILE="$RUNTIME_DIR/hirewise.log"
if [ ! -f "$ENV_FILE" ]; then
  echo 'Run startup_hosting/setup_pc.sh first.' >&2
  exit 1
fi
mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Hirewise is already running with PID $(cat "$PID_FILE")."
  exit 0
fi
set -a
. "$ENV_FILE"
set +a
cd "$ROOT_DIR"
umask 077
nohup "$ROOT_DIR/.venv/bin/gunicorn" config.wsgi:application \
  --bind 0.0.0.0:8000 --workers 2 --timeout 60 \
  --access-logfile - --error-logfile - >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
  echo "Hirewise failed to start. Review $LOG_FILE" >&2
  exit 1
fi
echo "Hirewise is running: http://10.40.23.128:8000"
echo "Logs: $LOG_FILE"
