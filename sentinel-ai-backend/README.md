# Sentinel AI — Backend

**"From Compliance Documents to Continuous Trust"**

AI-powered Governance, Risk & Compliance platform. This repo is the Python/FastAPI backend.

> **Status: Phase 1 complete.** PostgreSQL is loaded with **14,400 records** from the repository datasets
> across 15 datasets, **38 API endpoints** are live, and **61/61 tests pass**.
> Phase 2 (AI agents, RAG, Trust Score engine) has not been started.
>
> See `HANDOFF.md` for full context, `IMPLEMENTATION_STATUS.md` for the honest
> DONE/TODO tracker, and `NEXT_CLAUDE_PROMPT.md` for the continuation prompt.

## Quick start

```bash
bash scripts/bootstrap.sh          # postgres + deps + migrate + ingest + seed + test
uvicorn app.main:app --reload
# -> http://localhost:8000/api/v1/health
# -> http://localhost:8000/api/docs      (OpenAPI — all 38 endpoints)
```

Step by step, if you'd rather:

```bash
bash scripts/setup_postgres.sh     # PostgreSQL 16 + sentinel role + sentinel_ai db
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head               # creates all 18 tables
python -m app.ingestion.run        # loads all 15 datasets (idempotent)
python scripts/seed_users.py       # 5 demo users, one per role
python -m pytest                   # 61 tests
```

## What you can hit right now

```bash
curl localhost:8000/api/v1/dashboard | jq              # every figure a live query
curl localhost:8000/api/v1/risks/RISK-97985 | jq       # POLICY→CONTROL→FINDING→EVIDENCE→RISK
curl 'localhost:8000/api/v1/organization/graph?scope=full' | jq .data.meta
curl 'localhost:8000/api/v1/findings?status=Open&severity=High' | jq .meta
curl 'localhost:8000/api/v1/audit-logs?date_from=2026-07-01&min_risk_score=70' | jq .meta

curl -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sentinel.ai","password":"Sentinel@123"}'
```

Every response uses the same envelope:

```jsonc
{"data": [...], "meta": {"page":1,"page_size":25,"total":500,"total_pages":20}, "error": null}
```

## Ingestion

```bash
python -m app.ingestion.run                                  # all 15 datasets
python -m app.ingestion.run --dataset risks --dataset findings
python -m app.ingestion.run --list                           # dataset names
python -m app.ingestion.run --counts                         # live row counts
```

Safe to re-run: every table upserts on its natural-key primary key, so a second
run updates in place rather than duplicating. Verified by
`tests/test_ingestion.py::test_reingestion_does_not_duplicate`.

## Layout

```
app/
  core/          settings + security (bcrypt, JWT)
  database/      async SQLAlchemy engine + session
  models/        ORM models — 18 tables
  schemas/       Pydantic DTOs (response envelope + 15 resources + composites)
  repositories/  generic async data access
  services/      resource, dashboard, graph
  ingestion/     CSV -> Postgres pipeline + declarative per-dataset configs
  api/v1/        resource registry + routers
  main.py        app factory, CORS, exception handlers, router wiring
migrations/      Alembic (revision f6fd9ee3f6ac, applied)
datasets/        the 15 fictional demo CSVs (see datasets/README.md)
docs/profiling/  dataset profiling + relationship discovery output
scripts/         setup_postgres.sh, bootstrap.sh, seed_users.py
tests/           61 integration smoke tests
```

## Datasets

15 fictional demo datasets, 14,400 rows (see `datasets/README.md`). They were profiled and cross-referenced for
relationships *empirically* — by checking value overlap between every ID-like
column and every other file's primary key — before any model was written. See
`docs/profiling/` and `HANDOFF.md` §11.

Relationships that do **not** exist in the data (vendor→risk, report→finding,
personal-data→consent) are not fabricated anywhere in this codebase, including
in the organization graph.

## Trust Score

`/api/v1/dashboard` returns a Trust Score and Audit Readiness score. These are
**transparent deterministic** scores, not AI output: each response publishes its
own weights, components and formula so you can recompute it by hand. A test does
exactly that. Pass `?scores=off` for explicit nulls. The Phase 2 scoring engine
will replace them. Details in `HANDOFF.md` §12.
