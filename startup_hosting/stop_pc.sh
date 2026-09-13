#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PID_FILE="$ROOT_DIR/startup_hosting/runtime/hirewise.pid"
if [ ! -f "$PID_FILE" ]; then
  echo 'Hirewise is not running.'
  exit 0
fi
PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  COUNT=0
  while kill -0 "$PID" 2>/dev/null && [ "$COUNT" -lt 20 ]; do
    sleep 1
    COUNT=$((COUNT + 1))
  done
fi
if kill -0 "$PID" 2>/dev/null; then
  echo 'Server did not stop cleanly; inspect the process before taking further action.' >&2
  exit 1
fi
mv "$PID_FILE" "$PID_FILE.stopped"
echo 'Hirewise stopped.'
