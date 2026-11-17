#!/usr/bin/env bash
# One command from clean checkout to a running, data-loaded backend.
set -euo pipefail
cd "$(dirname "$0")/.."

bash scripts/setup_postgres.sh
pip install -e ".[dev]"
[ -f .env ] || cp .env.example .env

alembic upgrade head
python -m app.ingestion.run
python scripts/seed_users.py
python -m pytest

echo
echo "Start the API with:  uvicorn app.main:app --reload"
echo "Docs:                http://localhost:8000/api/docs"
