# SectorPulse

[中文说明](README.zh-CN.md) · [Verification](VERIFICATION.md) · [Original baseline](BASELINE.md)

A working sector-rotation research dashboard using FastAPI and React/TypeScript/Vite/Tailwind/Recharts. It compares the 11 SPDR sector ETFs with SPY, shows economic inputs, and explains deterministic rankings. Educational research only; not investment advice or a forecast.

## One local setup flow

Prerequisites: Python 3.12, Node.js 24 LTS, npm, and internet access for installation and live providers. Check out the branch containing this MVP, then run from the repository root on macOS/Linux:

```bash
cd sectorpulse-spec
bash run.sh
```

Open **http://127.0.0.1:8000**. The script creates a local virtual environment, installs locked dependencies, builds React, and starts FastAPI serving both the dashboard and API. Stop with Ctrl+C. Subsequent starts without reinstalling:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Live providers are the default. Select **Synthetic demo**, then **Refresh analysis**, for a reproducible demonstration without provider access. Synthetic data is always labeled and is never silently substituted for live data. Data source preference persists in browser localStorage. No login is required.

Optional FRED configuration: copy `.env.example` to `.env` in the repository root, put your FRED key in it, and restart the server. Alternatively set `FRED_API_KEY` in the server environment. No key goes into the frontend. No Anthropic key is needed. `.env` files are ignored by Git and Docker.

## Implemented

- Health, price history, macro snapshot, and analysis endpoints; interactive refresh and completion timestamp.
- Ranking table, sector detail explanations, indexed growth and adjusted-dollar charts against SPY.
- Macro observation dates, units, ages, source attribution, partial coverage, missing key, loading, empty, and API-error states.
- Per-ticker retries, empty-response retries, bounded provider calls, invalid-value rejection, historical cutoff, deterministic tie-breaking, and common-window comparisons without filling gaps.
- Responsive layout; ranking tables scroll within their panel on narrow screens.
- Browser preference storage only. There is no server-side database or saved-run history.

## Architecture

```text
Browser (React + TypeScript + Recharts)
  └─ /api → FastAPI
               ├─ validated historical cutoff
               ├─ Yahoo Finance adjusted prices
               ├─ optional FRED/ALFRED macro observations
               └─ deterministic scoring → structured JSON
```

The production build is served by FastAPI on the same origin. Development uses Vite's API proxy. Neither mode exposes API keys to the browser. Synthetic demo data follows the same analysis path but never calls live providers.

```text
backend/app/config.py       ETF universe, sector names, cycle mapping
backend/app/data/            Live fetchers and synthetic fixtures
backend/app/analysis.py      Relative performance and cycle scoring
backend/app/main.py          API routes and frontend hosting
backend/tests/              Configuration, provider, scoring, API tests
frontend/src/               Dashboard, charts, and responsive styles
eval/score.py               Combined verification command
run.sh                     Local installation, build, and launch
Dockerfile / compose.yaml  Deployment configuration
```

## Methodology and historical semantics

`as_of_date` is inclusive, defaults to yesterday in America/New_York, and accepts 1999-01-01 through yesterday. Today's potentially unfinished session and future dates are rejected. Yahoo's exclusive end is requested as the next date, then the response is filtered again. Weekends use the last available session. Prices older than seven calendar days cannot establish a benchmark.

All ranked sectors must have valid positive prices on SPY's latest 61 observed sessions. Incomplete sectors are excluded with reasons. This strict policy may produce few rankings during partial provider outages; it does not manufacture missing observations.

For 20 and 60 sessions, excess return is `(sector end/start − SPY end/start) × 100`, in percentage points. Score is `0.4 × excess20 + 0.6 × excess60 + cycle bonus`. The bonus is two points for sectors in the existing cycle mapping, otherwise zero. Ties resolve alphabetically. This heuristic has not been validated for predictive performance.

Cycle context uses the unemployment change over three observation intervals and the latest 10Y−2Y Treasury spread:

- Unemployment rise of at least 0.3 percentage points: contraction.
- Otherwise an inverted spread: slowdown.
- Otherwise unemployment decline of at least 0.2 points: recovery.
- Otherwise expansion.

Missing or stale inputs yield unknown context and zero cycle bonus. Unemployment must be no older than 75 days and the spread no older than 10 days. Other macro series are displayed for context, not fed into this initial cycle rule. MANEMP is correctly labeled manufacturing employment, not PMI; the OECD CLI is not labeled the Conference Board LEI. CPI is an index level, not an inflation rate.

FRED requests restrict both observations and the real-time vintage to the selected date, following [FRED's real-time API parameters](https://fred.stlouisfed.org/docs/api/fred/series_observations.html). A missing key or unavailable series does not prevent price analysis. Yahoo adjusted history can be revised after the requested date; this is not a certified point-in-time backtest. A date cutoff alone cannot eliminate all historical bias.

## API

Interactive schema: `/docs`. Dates use `YYYY-MM-DD`; `mode` is `live` or `demo`.

| Endpoint | Result |
| --- | --- |
| `GET /api/health` | Process health and boolean feature configuration; no credentials |
| `GET /api/prices?as_of_date=2025-01-31` | Adjusted prices by ticker, source, unavailable tickers |
| `GET /api/macro?as_of_date=2025-01-31` | All macro indicators with explicit available/unavailable states |
| `GET /api/analysis?as_of_date=2025-01-31&mode=demo` | Ranking, score components, context, charts, macro, exclusions, timestamps and limitations |

Invalid input returns 422; complete price failure or an unusable benchmark returns 503 with a safe error code and message. Partial sector failures return the usable data with exclusions. Health is process liveness, not a guarantee of provider availability. Provider calls run in FastAPI's worker threads. Requests may take several minutes if every provider attempt times out; this MVP has no background job queue or shared cache.

## Development and checks

After local setup, from the repository root:

```bash
.venv/bin/python eval/score.py
```

This runs pytest, Ruff, mypy, frontend type checking, linting, and production build. Missing check tools fail rather than being treated as success.

For hot reload, in two terminals:

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to port 8000. Restart Vite if a filesystem watcher misses changes.

## Deployment configuration (not deployed)

The multi-stage Dockerfile builds the frontend and serves it with FastAPI on the same origin. This avoids browser CORS and keeps provider credentials on the server.

Local container verification, with Docker running:

```bash
docker compose up --build
```

Open http://127.0.0.1:8000. Compose binds only to localhost. It forwards an optional `FRED_API_KEY` from the environment or local `.env` without copying that file into the image.

For a container host of your choice: build with `docker build -t sectorpulse .`, configure container port 8000 and health path `/api/health`, inject `FRED_API_KEY` through the host's secret manager, and enable HTTPS at the host's ingress. The image runs as a non-root user. Do not expose the raw provider-fetching endpoint to large public traffic without rate limiting, caching, and concurrency limits at the ingress. This configuration is intended for a private/small MVP deployment.

For separate frontend/backend hosting: run `npm ci && npm run build` in `frontend`, serve `frontend/dist`, and configure the frontend host to reverse-proxy `/api/*` to the private FastAPI service **preserving the `/api` prefix**. Forward `/docs` and `/openapi.json` only if desired. Configure a proxy timeout appropriate for provider retries (up to 15 minutes in a full outage). No client-side API key or permissive CORS setting is required. Both deployments require the same source version.

No external service was deployed and no account was created. Docker daemon availability is required to validate the image; see VERIFICATION.md for checks performed here.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Port 8000 is already in use | Stop the previous SectorPulse process, or start Uvicorn on another port and open that port. For Vite development, also update its proxy target. |
| FRED inputs are unavailable | Set `FRED_API_KEY` on the server and restart. Price ranking still works without it. |
| Only some sectors are ranked | Read the exclusion reasons. A sector needs all 61 benchmark sessions; use Refresh to retry the provider. |
| Live data cannot load | Check provider/network availability or explicitly select Synthetic demo. Demo is never an automatic fallback. |
| The dashboard is missing at `/` | Build `frontend/dist` with `npm run build`, then restart FastAPI. |
| You see old frontend changes | Rebuild for production; for development, restart Vite if file watching missed a change. |

## Remaining limitations

AI agents/narratives, RRG visualization, allocation recommendations, database persistence, saved analysis runs, authentication, exchange-calendar validation, scheduled refreshes, and a production cache/job queue are not implemented. AI is explicitly disabled; no prompts or dates are sent to an LLM. The empty `agents` and `db` packages preserve extension points without claiming functionality. Browser settings are device-local. FRED live success needs a real key and was not verified without one. Provider licensing, availability, and revision behavior must be considered before broader commercial use.
