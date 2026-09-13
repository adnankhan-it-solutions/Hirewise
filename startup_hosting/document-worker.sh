#!/bin/sh
set -eu
while true; do
  python manage.py process_documents
  sleep 15
done
