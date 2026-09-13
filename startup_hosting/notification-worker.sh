#!/bin/sh
set -eu
while true; do
  python manage.py deliver_notifications
  sleep 30
done
