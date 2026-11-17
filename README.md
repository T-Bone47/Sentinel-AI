# Sentinel AI

**"From Compliance Documents to Continuous Trust"** — an AI-powered Governance, Risk
& Compliance platform. Full-stack: React/TypeScript frontend, FastAPI/PostgreSQL backend,
**14,400 records** across 15 datasets (fictional demo data generated with ChatGPT: see `sentinel-ai-backend/datasets/README.md`).

> **Phase 2B backend intelligence is live**: Evidence Intelligence, Policy
> Intelligence and a Compliance Copilot, all answering from the loaded datasets.
> **105 backend tests pass.** Their frontend panels are not built yet — see
> `HANDOFF.md` § PHASE 2B.
>
> **Status: the frontend is wired to the real backend.** 19 of 21 data screens read live
> Postgres data through the API. No screen silently falls back to sample data — if the
> backend is down, the UI says so.
>
> See `HANDOFF.md` for the full picture, `IMPLEMENTATION_STATUS.md` for the honest
> done/remaining tracker, and `NEXT_CLAUDE_PROMPT.md` to continue the work.

## Run it

Two terminals. **Backend first** — the frontend shows a connection error without it.

```bash
# 1 — backend (PostgreSQL + FastAPI)
cd sentinel-ai-backend
bash scripts/setup_postgres.sh      # PostgreSQL 16 + sentinel_ai database
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head                # 18 tables
python -m app.ingestion.run         # loads all 15 datasets (idempotent)
python scripts/seed_users.py        # demo logins
uvicorn app.main:app --reload       # http://localhost:8000/api/docs
```

```bash
# 2 — frontend
npm install
npm run dev                         # http://localhost:5173
```

`vite.config.ts` proxies `/api` to `localhost:8000`, so no CORS setup and no `.env`
is needed for local development.

## The demo path

1. **Command Center** — Trust Score, Audit Readiness, critical risks, evidence
   coverage, framework rollup, live audit activity. Every figure is a live query.
2. Click a **critical risk** → the investigation drawer opens.
3. Follow **POLICY → CONTROL → FINDING → EVIDENCE → RISK** through real foreign keys.
4. **Organization Graph** — one API call returns the whole topology.
5. **Employees / Identity / Devices / Applications / Cloud / Vendors** — records from the repository datasets.
6. **DPDP Inventory / Consent**, **Evidence**, **Audit Logs**, **Reports**.

## Trust Score honesty

The score on the Command Center is a **transparent deterministic** calculation, not a
model output. The hero panel shows its actual components, weights and formula, straight
from the backend, so a reviewer can recompute the number by hand. It is labelled
`deterministic_phase1`. The Phase 2 scoring engine will replace it.

For the same reason the UI does **not** show a trust trend, a week-on-week delta, or a
risk-velocity chart: Phase 1 stores a single snapshot with no history, so those would
have been invented. They were replaced with real distributions.

## Layout

```
src/
  services/      http.ts · types.ts · adapters.ts · api.ts   <- the integration layer
  hooks/         useApiResource.ts (loading / error / retry)
  components/    UI system, charts, graph canvas, drawers (unchanged design)
  pages/         21 screens
  data/          seed data — retained for reference only, not a runtime fallback
sentinel-ai-backend/
  app/           FastAPI, SQLAlchemy models, ingestion, services, routers
  datasets/      the 15 fictional demo CSVs (see datasets/README.md)
  migrations/    Alembic
  tests/         61 integration tests
```

## Demo logins

All use password `Sentinel@123` (seeded by `scripts/seed_users.py`, demo only):
`admin@sentinel.ai` · `compliance@sentinel.ai` · `security@sentinel.ai` ·
`auditor@sentinel.ai` · `employee@sentinel.ai`


## Intelligence APIs (Phase 2B)

```bash
# Evidence: can we prove our controls work?
curl localhost:8000/api/v1/intelligence/evidence | jq
curl localhost:8000/api/v1/intelligence/evidence/coverage | jq '.data.by_framework'
curl localhost:8000/api/v1/intelligence/controls/CTRL-10128/evidence | jq

# Policy: extract requirements and map them to real controls
curl -X POST localhost:8000/api/v1/intelligence/policy/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"All privileged accounts must use multi-factor authentication."}' | jq

# Copilot: ask a question, get a structured answer from live data
curl -X POST localhost:8000/api/v1/copilot/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Are we audit ready?"}' | jq
```

### Honesty guarantees, enforced by tests

- **Evidence coverage** counts a control only when it has *verified* evidence.
  The formula ships in the response. No severity weighting inflates it.
- **Evidence freshness is not judged.** Ages are real; "stale" is not derivable
  from this dataset, so nothing claims it (`freshness_policy_available: false`).
- **No LLM is configured.** Policy analysis and the Copilot are deterministic,
  and every response carries `llm_used: false`.
- **Unmappable policy requirements** return `"No verified control mapping
  found."` — never a nearest guess.
- **Out-of-scope Copilot questions** decline and list what can be answered.

## License

Apache License 2.0; see [LICENSE](LICENSE).
- The demo datasets are fictional; see `sentinel-ai-backend/datasets/README.md`.
- Third-party samples keep their own licences; see `docs/DATA_PROVENANCE.md`.
