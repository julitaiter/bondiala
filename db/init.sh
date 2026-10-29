#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_user="$DB_USER" --set=app_password="$DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEROLE PASSWORD %L', :'app_user', :'app_password') \gexec
SELECT format('GRANT CONNECT, CREATE ON DATABASE %I TO %I', current_database(), :'app_user') \gexec
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'app_user') \gexec
CREATE EXTENSION IF NOT EXISTS postgis;
SQL
if [ "${DB_ALLOW_CREATEDB:-false}" = "true" ]; then
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_user="$DB_USER" <<'SQL'
SELECT format('ALTER ROLE %I CREATEDB', :'app_user') \gexec
CREATE DATABASE template_bondiala;
SQL
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname template_bondiala -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c 'ALTER DATABASE template_bondiala IS_TEMPLATE true;'
fi
