#!/bin/sh
set -eu
umask 077
backup_dir=${BACKUP_DIR:-./backups}
mkdir -p "$backup_dir"
backup_path="$backup_dir/bondiala-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$backup_path.tmp"
mv "$backup_path.tmp" "$backup_path"
printf 'Backup creado: %s\n' "$backup_path"
