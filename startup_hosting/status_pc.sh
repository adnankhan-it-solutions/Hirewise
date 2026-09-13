#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PID_FILE="$ROOT_DIR/startup_hosting/runtime/hirewise.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Hirewise is running with PID $(cat "$PID_FILE")."
  curl -fsS http://127.0.0.1:8000/health/
  printf '\nLAN address: http://10.40.23.128:8000\n'
else
  echo 'Hirewise is not running.'
  exit 1
fi
