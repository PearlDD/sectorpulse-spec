# SectorPulse

[中文说明](README.zh-CN.md) · [Verification](VERIFICATION.md) · [Original baseline](BASELINE.md)

A browser-based sector research dashboard for the 11 SPDR sector ETFs and SPY. FastAPI, React, TypeScript, Vite, Tailwind and Recharts remain the foundation. Version 0.3 adds saved evidence, background jobs, independent risk/macro context and fixed-rule validation.

**Educational research only. Not investment advice, a forecast, or a claim of predictive advantage.**

## Run locally

Prerequisites: Python 3.12, Node.js 24 LTS, npm, macOS or Linux, and internet access for installation/live providers. From this repository:

```bash
bash run.sh
```

Open **http://127.0.0.1:8000**. This creates `.venv`, installs locked dependencies, builds React and starts FastAPI serving the UI and API together. Stop with Ctrl+C. Subsequent starts:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Choose **Live providers** or **Synthetic demo**, choose a cutoff, then click **Refresh analysis**. Opening the dashboard only reads saved results; it does not fetch or bill a provider. Demo never silently replaces failed live data. Source preference is stored in browser localStorage.

Optional: copy `.env.example` to `.env` at the repository root and restart after setting `FRED_API_KEY` and/or `ANTHROPIC_API_KEY`. Both are server-only. Without FRED, prices still work and macro inputs show unavailable. Without Anthropic, deterministic research still works and the AI button is disabled. Never put keys in `VITE_*` variables or commit `.env`.

## What works

- Explicit background refresh, visible stages and timestamps, durable queued/running/succeeded/failed/timed_out/interrupted states.
- SQLite saved-run journal, original sanitized price/macro snapshots, SHA-256 fingerprints, and deterministic replay verification.
- History selection, price and indexed-performance charts vs SPY, sector details, independent risk measurements, macro availability/age, and desktop/mobile layouts.
- Comparable sector ranking with coverage gating, partial-data explanations and last successful reports retained after failures.
- A transparent relative-strength map with trails; this is **not the proprietary JdK RRG calculation**.
- Retrospective temporal holdout, inspectable signal/entry/exit periods, skipped-period reasons in JSON, illustrative costs and explicit limitations.
- Optional Anthropic explanation requested separately. Its failure never changes the deterministic report.

## Calculation and reliability contract

`as_of_date` is inclusive and defaults to yesterday in America/New_York. Supported dates are 1999-01-01 through yesterday; unfinished current-day and future cutoffs are rejected. Yahoo's exclusive end is the following date and returned rows are filtered again. Providers have bounded timeouts and retries; invalid, nonpositive, nonfinite or duplicate observations are sanitized. No missing prices are forward-filled.

The comparison window is SPY's latest 61 observed sessions, with the last observation no more than seven calendar days before cutoff. Every included sector needs all those dates. Sector launch dates determine eligibility. Fewer than 80% of eligible sectors means ordinal ranks and the leader label are withheld; no usable sectors or benchmark fails the task.

For each window, excess return in percentage points is `(sector end/start − SPY end/start) × 100`. Strength is:

```text
0.4 × 20-session excess return + 0.6 × 60-session excess return
```

Ties use ticker order. The weights are fixed descriptive heuristics, not fitted or validated as optimal. **The former fixed cycle bonus is removed.** Absolute returns, annualized 60-return volatility (sample standard deviation × √252), and maximum drawdown over the 61-price window remain separate. Labor, inflation, stress and yield-curve evidence do not alter ranks or force a business-cycle label. Stale/missing evidence is marked unavailable.

The custom map uses X = 100 × ((sector/SPY)/(sector/SPY 20 sessions earlier) − 1); Y = X minus X five sessions earlier. Six recent points form a trail. Quadrants describe relative leadership and its change, not future direction.

FRED restricts both observations and real-time vintage to cutoff using [official real-time parameters](https://fred.stlouisfed.org/docs/api/fred/series_observations.html). Yahoo adjusted history can be revised retrospectively. A snapshot preserves exactly what this app used, but is not proof that these prices were available historically. SPY observed sessions substitute for a full exchange calendar.

### Validation, without inflated claims

The fixed rule reserves the first 60% of history and evaluates the last 40%, requiring at least 504 benchmark observations. Every 21 sessions, it selects the top three using only information through the signal close, enters at the next observed close, and exits 20 sessions later. Missing forward observations skip the entire period; there is no replacement chosen using future information. Both the equally weighted basket and SPY pay an illustrative 20 bps round-trip cost per period. At least six usable periods and no more skipped than usable periods are needed for summary metrics.

This is a **retrospective temporal holdout**, not an untouched prospective test or a continuous portfolio simulation. It reports period mean excess return and outperformance frequency, not CAGR or a significance claim. There is no parameter tuning. See [the recorded live result](eval/reports/validation-2025-12-31.json): 18 periods, mean excess **−0.0555 percentage points**, which does not establish an advantage. Synthetic checks are mechanics demonstrations only.

### Optional AI

A separate action sends an explicit whitelist of ticker symbols, numerical relative/absolute/risk measurements, coverage counts and synthetic-data status to Anthropic. No calendar dates, price history, snapshot metadata, credentials or free-form provider text enter the prompt. The API requests [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs); the output is schema-validated and stored separately with model, prompt version and input fingerprint. It cannot write rankings or snapshots. Date omission reduces one information channel; it does not prove an LLM is free of historical knowledge or hallucination. AI text remains unverified. No automatic AI request or billing retry occurs.

## Architecture and storage

```text
React browser → FastAPI → SQLite journal
                            └─ single dispatcher → bounded worker subprocess
                                 ├─ Yahoo / optional FRED → saved input snapshot
                                 ├─ strength + risk + macro + holdout → saved run
                                 └─ optional Anthropic → separate explanation
```

Default storage is `<repository>/data/sectorpulse.db`; override with `SECTORPULSE_DB` using an absolute path. The database and credentials are ignored by Git/Docker. A single worker consumes a queue capped at four active jobs; duplicate active requests share a job. Analysis has a 15-minute wall limit, AI 90 seconds. Restart marks unfinished jobs interrupted; retry is explicit. Closing a browser does not cancel work while the server stays running. This is background processing, **not a scheduled refresh service**.

Run **one Uvicorn worker and one instance per database**. A local file lock rejects concurrent dispatchers. SQLite needs a persistent local filesystem; this design is not for serverless ephemeral disks or multiple replicas. For backup, stop the app and copy the database, or use SQLite's online backup API. No automatic retention/deletion or migration from old PR report databases is implemented.

| Area | Files |
| --- | --- |
| API and hosting | `backend/app/main.py` |
| Universe, fetchers, snapshots | `backend/app/config.py`, `backend/app/data/` |
| Strength, risk, macro, map | `backend/app/analysis.py` |
| Temporal validation | `backend/app/validation.py` |
| Journal and background worker | `backend/app/db/store.py`, `backend/app/services/jobs.py` |
| Optional narrative | `backend/app/services/explanation.py` |
| Browser UI and charts | `frontend/src/App.tsx`, `ResearchCharts.tsx`, `api.ts` |

## API

Interactive schema: `/docs`. Dates use `YYYY-MM-DD`; modes are `live` and `demo`.

| Endpoint | Behavior |
| --- | --- |
| `GET /api/health` | Liveness, version and boolean key configuration; not provider readiness |
| `POST /api/runs` | JSON `{"mode":"demo","as_of_date":"2025-12-31"}` → 202 with job |
| `GET /api/jobs`, `/api/jobs/{id}` | Durable state, stage and safe errors |
| `GET /api/runs?mode=live&limit=20&offset=0` | Paginated successful/partial reports |
| `GET /api/runs/latest?mode=live`, `/api/runs/{id}` | Saved structured analysis |
| `GET /api/runs/{id}/snapshot` | Original sanitized inputs and fingerprint |
| `GET /api/runs/{id}/replay` | Recalculate saved inputs and compare with saved result |
| `GET /api/runs/{id}/explanation` | Optional saved narrative and configuration state |
| `POST /api/runs/{id}/explanation` | Queue explicit AI request or return cached explanation |
| `GET /api/analysis`, `/api/prices`, `/api/macro` | Compatibility routes: read latest saved report; **never fetch** |

Compatibility routes accept mode and optional as_of_date; a date mismatch returns 404 rather than fetching. v0.2 clients must migrate refreshes to POST and poll job state. Invalid input returns 422, missing records 404, full queue 429, missing AI configuration 503, and incompatible replay method 409. Provider failures after acceptance are visible in the job, not disguised as an HTTP-success analysis.

## Development and verification

After setup:

```bash
.venv/bin/python eval/score.py
```

Runs pytest, Ruff, mypy, strict TypeScript, ESLint and production build. For development, start the backend with `--reload --port 8000`, then in another terminal run `cd frontend && npm run dev`. Open http://127.0.0.1:5173; Vite proxies `/api` to port 8000.

## Deployment configuration (not deployed)

Recommended: serve frontend and backend together using the supplied multi-stage Dockerfile:

```bash
docker compose up --build
```

Open http://127.0.0.1:8000. Compose binds to localhost, passes optional keys server-side, and mounts the `research-data` named volume at `/app/data`. The image runs as a non-root user. Do not use `docker compose down -v` if you want to keep saved runs.

On a container host, build this image, keep one instance/worker, mount persistent storage writable by the application user, set `SECTORPULSE_DB=/app/data/sectorpulse.db`, inject keys through its secret manager, expose port 8000 behind HTTPS, and use `/api/health` for liveness. Use an access-controlled ingress for private use. There is no login; anyone who can reach the API can read the shared journal and trigger provider/AI work. The local queue cap is not per-user rate limiting.

For separate hosting, build `frontend` with `npm ci && npm run build`, serve `frontend/dist`, and reverse-proxy `/api/*` to FastAPI preserving the `/api` prefix. Keep API keys and SQLite on the backend host. No client-side keys or broad CORS policy is necessary. Refresh returns promptly; the browser polls, so no 15-minute proxy request timeout is needed. Use the same source version for both services.

No external deployment or account creation has been performed. Container execution requires a working Docker daemon; current verification limits are recorded separately.

## Remaining limitations / troubleshooting

- Live provider outages can yield partial or failed runs. Read exclusions/job errors, then retry explicitly; last saved research remains readable.
- AI live verification failed in this environment; mocked contract/success/failure paths pass. Key configuration alone does not prove provider access.
- FRED live success has not been verified without a real configured key. Missing-key and vintage/failure behavior are tested.
- No licensed point-in-time price feed, full exchange calendar, transaction-cost calibration, statistically established edge, portfolio allocation, authentication, scheduled refresh or multi-user settings.
- If `/` is missing, build `frontend/dist`. If port 8000 is busy, use another backend port (and update the Vite proxy for development). After production frontend changes, rebuild and reload the browser.
- History stores sensitive research context in a shared local journal. Raw snapshots can be large; provider licensing and data retention need consideration before broader distribution.
