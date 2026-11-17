#!/usr/bin/env bash
# Exact PostgreSQL setup used to build the Review-1 database, on Ubuntu 24.04.
# Idempotent: safe to re-run.
set -euo pipefail

apt-get update -q || true
apt-get install -y -q postgresql

# The container image has no init system, so start the cluster directly.
pg_ctlcluster 16 main start || true

su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='sentinel'\"" | grep -q 1 \
  || su postgres -c "psql -c \"CREATE USER sentinel WITH PASSWORD 'sentinel' SUPERUSER;\""

su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='sentinel_ai'\"" | grep -q 1 \
  || su postgres -c "createdb -O sentinel sentinel_ai"

PGPASSWORD=sentinel psql -h 127.0.0.1 -U sentinel -d sentinel_ai -c "SELECT version();"
echo "PostgreSQL ready: postgresql://sentinel:sentinel@localhost:5432/sentinel_ai"
