#!/bin/sh
set -eu
mc alias set local http://object-storage:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$PRIVATE_BUCKET"
mc anonymous set none "local/$PRIVATE_BUCKET"
