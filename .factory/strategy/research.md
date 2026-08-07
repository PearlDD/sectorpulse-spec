# Research Report — SectorPulse Web App

## Project Summary

SectorPulse is a full-stack web app (FastAPI + React/Vite) that wraps the existing V2 sector rotation agent pipeline to deliver AI-driven sector rotation analytics via a browser UI. The agent pipeline (macro analyst → sector analyst → portfolio allocator) already exists in the `sector-rotation-analytics-agent-vs-automation-arc` repo and uses Claude via `langchain-anthropic` with structured output (Pydantic models). The web app adds: scheduled daily runs, historical report storage, on-demand analysis, and visual dashboards including RRG charts.

---

## 1. Existing Code Analysis

### What Can Be Reused As-Is

| File | What It Does | Reuse Notes |
|---|---|---|
| `src/config.py` | SECTOR_TICKERS, SECTOR_LAUNCH_DATES, FRED_SERIES, FRED_SERIES_V2, CYCLE_SECTOR_MAP, get_available_sectors() | Copy directly. Remove backtest-specific constants (START_DATE, END_DATE, TRANSACTION_COST_BPS, etc.) |
| `src/agent_v2/agents/macro_analyst.py` | CyclePhase model + `analyze()` — classifies business cycle via Claude structured output | Copy directly. Already date-free in prompts (critical rule satisfied). |
| `src/agent_v2/agents/sector_analyst.py` | SectorAnalysis/SectorScore models + `analyze()` — scores all 11 sectors | Copy directly. Already date-free. |
| `src/agent_v2/agents/portfolio_allocator.py` | PortfolioAllocation model + `allocate()` — produces top-5 weighted allocation | Copy directly. Already date-free. |

### What Needs Adaptation

| File | Changes Needed |
|---|---|
| `src/agent_v2/orchestrator.py` | Heavy adaptation. Currently designed for backtesting (triple-run median, BacktestState). For the web app: (1) single-run instead of triple-run (saves 2/3 Claude API cost), (2) remove BacktestState's backtest-specific fields, (3) add narrative generation step (new node), (4) return a richer result object for the frontend. |
| `src/data/fetcher.py` | Moderate adaptation. Remove backtest-specific ALFRED vintage logic. Keep `fetch_sector_prices()` and `fetch_macro_indicators()` / `fetch_macro_v2_indicators()`. Adapt to fetch "latest" data only (not historical ranges). Remove parquet storage dependency — return DataFrames directly for the pipeline, persist results to SQLite via a separate layer. |

### What's New (Not in Existing Code)

- **Narrative generator agent** — new Claude call that takes macro analysis + sector scores + allocation and generates the "Market Cycle Narrative" and per-sector "WHY" explanations
- **RRG quadrant classifier** — pure math, no LLM needed (see Section 3)
- **Oversold detector** — compare price momentum vs fundamental indicators to find divergences
- **SQLite persistence layer** — store analysis reports as JSON blobs with timestamps
- **APScheduler integration** — daily 4:30 PM ET cron trigger
- **Full React frontend** — dashboards, charts, history browser

---

## 2. Recommended Project Structure

```
sectorpulse/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, lifespan, mount static
│   │   ├── config.py            # Sector tickers, FRED series (from existing)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py        # /api/reports, /api/reports/latest, /api/run, /api/sectors
│   │   │   └── deps.py          # Dependency injection (DB session, rate limiter)
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── macro_analyst.py     # From existing V2
│   │   │   ├── sector_analyst.py    # From existing V2
│   │   │   ├── portfolio_allocator.py # From existing V2
│   │   │   ├── narrative_gen.py     # NEW: generates WHY explanations
│   │   │   └── orchestrator.py      # Adapted: single-run + narrative step
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── fetcher.py       # Adapted from existing (latest-only)
│   │   │   └── rrg.py           # NEW: RRG quadrant math
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py        # SQLAlchemy models (Report, SectorSnapshot)
│   │   │   ├── database.py      # async engine + session factory
│   │   │   └── crud.py          # create_report, get_reports, get_latest
│   │   └── scheduler.py         # APScheduler setup (daily 4:30 PM ET)
│   ├── pyproject.toml
│   └── alembic/                 # DB migrations (optional for MVP)
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Hot Sectors + Scorecard
│   │   │   ├── RRGChart.tsx     # Relative Rotation Graph
│   │   │   ├── History.tsx      # Past reports browser
│   │   │   └── Report.tsx       # Single report detail
│   │   ├── components/
│   │   │   ├── SectorCard.tsx
│   │   │   ├── NarrativePanel.tsx
│   │   │   ├── RRGPlot.tsx      # Recharts scatter plot
│   │   │   └── RunButton.tsx    # On-demand trigger
│   │   └── api/
│   │       └── client.ts        # fetch wrapper for /api/*
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── tailwind.config.js
├── .env.example                 # FRED_API_KEY, ANTHROPIC_API_KEY
├── pyproject.toml               # Root (optional, for workspace tooling)
└── README.md
```

### Serving Strategy

FastAPI serves the built React app as static files from `frontend/dist/`. In development, Vite dev server runs on port 5173 with proxy to FastAPI on 8000. In production, `npm run build` outputs to `frontend/dist/`, and FastAPI mounts it:

```python
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="spa")
```

API routes are prefixed `/api/` so they don't conflict with the SPA catch-all.

---

## 3. RRG Quadrant Model — Implementation Plan

The RRG is pure math — no LLM needed. Algorithm (based on Julius de Kempenaer methodology):

### Step 1: Relative Strength
```python
RS = (sector_price / benchmark_price) * 100  # SPY as benchmark
```

### Step 2: JdK RS-Ratio (double-smoothed)
```python
RS_smooth = WMA(RS, window=10)          # Weighted Moving Average
RS_benchmark = WMA(RS_smooth, window=10) # Second smoothing
RS_Ratio = (RS_smooth / RS_benchmark) * 100  # Normalized around 100
```

### Step 3: JdK RS-Momentum
```python
RS_Momentum = (RS_Ratio / RS_Ratio_prev) * 100  # Rate of change, normalized around 100
```

### Step 4: Quadrant Classification
| Quadrant | RS-Ratio | RS-Momentum | Meaning |
|---|---|---|---|
| Leading | > 100 | > 100 | Outperforming, gaining momentum |
| Weakening | > 100 | < 100 | Outperforming, losing momentum |
| Lagging | < 100 | < 100 | Underperforming, losing momentum |
| Improving | < 100 | > 100 | Underperforming, gaining momentum ← **Next-Hot candidates** |

The "Improving" quadrant directly maps to the **Next-Hot Predictor** feature. Sectors moving from Lagging → Improving are the turnaround candidates.

### WMA Implementation
```python
def wma(data: pd.Series, window: int = 10) -> pd.Series:
    weights = np.arange(1, window + 1)
    return data.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum())
```

---

## 4. Architecture Patterns

### API Design

```
GET  /api/reports              — list reports (paginated, newest first)
GET  /api/reports/latest       — most recent report
GET  /api/reports/{id}         — single report by ID
POST /api/run                  — trigger on-demand analysis (rate-limited 3/day)
GET  /api/sectors              — current sector scorecard (latest snapshot)
GET  /api/sectors/rrg          — RRG data (RS-Ratio, RS-Momentum per sector)
GET  /api/health               — health check
```

### Data Flow

```
[Scheduler / Manual Trigger]
       │
       ▼
  fetch_sector_prices()  ──→  yfinance (11 ETFs + SPY)
  fetch_macro_indicators() ──→ FRED API
       │
       ▼
  compute_rrg()  ──→  pure math (RS-Ratio, RS-Momentum, quadrant)
       │
       ▼
  orchestrator.run()
    ├── macro_analyst.analyze(macro_data)     → CyclePhase
    ├── sector_analyst.analyze(sectors, ...)  → SectorAnalysis
    ├── portfolio_allocator.allocate(...)     → PortfolioAllocation
    └── narrative_gen.generate(...)           → NarrativeReport (NEW)
       │
       ▼
  save_report(db, result)  ──→  SQLite
       │
       ▼
  Frontend polls / fetches latest report
```

### APScheduler Integration Pattern

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_analysis,
        CronTrigger(hour=16, minute=30, timezone="US/Eastern"),
        id="daily_analysis",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

### SQLite Schema (MVP)

```sql
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trigger TEXT CHECK(trigger IN ('scheduled', 'manual')),
    cycle_phase TEXT,
    cycle_confidence REAL,
    risk_level TEXT,
    narrative TEXT,          -- AI-generated market story
    sector_scores JSON,     -- full SectorAnalysis as JSON
    allocation JSON,        -- PortfolioAllocation as JSON
    rrg_data JSON,          -- RS-Ratio/Momentum per sector
    raw_macro_data JSON     -- input macro indicators (for reproducibility)
);
```

Using `aiosqlite` via SQLAlchemy async engine (`sqlite+aiosqlite:///data/sectorpulse.db`).

---

## 5. Potential Pitfalls

### yfinance Rate Limits
- **Risk**: Yahoo Finance throttles at ~2000 requests/hour; HTTP 429 errors.
- **Mitigation**: Only fetching 12 tickers (11 sectors + SPY) once per run. Add 1-2 second delays between tickers. Cache prices in SQLite — only fetch new data since last run. The existing `_retry_with_backoff` in fetcher.py already handles transient failures.
- **Fallback**: If yfinance breaks entirely (has happened before), consider `yfinance` alternatives like `yahoo_fin` or switch to Polygon.io free tier.

### FRED API Keys
- **Risk**: FRED API requires a free key. Missing key = no macro data.
- **Mitigation**: Fail gracefully — if no FRED key, run analysis with price data only (RRG still works). Show a warning banner in the UI. Document the key setup clearly in README and `.env.example`.
- **Rate limit**: 120 requests/minute (generous). With 9 series total, not a concern.

### Claude API Costs
- **Risk**: Each analysis run invokes Claude 3-4 times (macro + sector + allocator + narrative). At ~$0.02-0.10 per call depending on model, daily scheduled + 3 manual = ~4 runs/day = ~$0.50-1.50/day.
- **Mitigation**: Use `claude-sonnet-4-6` instead of `claude-opus-4-6` for the web app (much cheaper, fast enough for structured output). Single-run instead of triple-run saves 2/3 cost. Rate-limit manual runs to 3/day as spec requires. Consider caching — if macro data hasn't changed, skip re-analysis.
- **Model choice**: The existing code uses `claude-opus-4-6`. For SectorPulse, switch to `claude-sonnet-4-6` — the structured output tasks (cycle classification, sector scoring) don't need Opus-level reasoning, and Sonnet is 5-10x cheaper.

### Anti-Look-Ahead Bias (Critical Rule)
- **Risk**: The spec mandates no dates in prompts. The existing agent code already handles this correctly — `decision_date` is accepted for API compatibility but never passed to the LLM.
- **Mitigation**: The narrative generator (new) must also follow this rule. Pass only numerical values, never dates. Add a unit test that greps agent prompts for date patterns.

### yfinance Data Quality
- **Risk**: yfinance occasionally returns stale or incomplete data, especially outside market hours.
- **Mitigation**: Validate that price data is recent (within 3 trading days). If stale, show a "data may be delayed" warning. Schedule runs at 4:30 PM ET (after market close) when data is most reliable.

### SQLite Concurrency
- **Risk**: SQLite has limited write concurrency. Concurrent scheduler + manual runs could conflict.
- **Mitigation**: Use WAL mode (`PRAGMA journal_mode=WAL`) for concurrent reads during writes. Analysis runs are infrequent (max ~4/day), so contention is negligible. For MVP, this is a non-issue.

---

## 6. MVP Scope Recommendation

### Phase 1: Core Pipeline (build first)
1. Port agent code (macro_analyst, sector_analyst, portfolio_allocator, config)
2. Adapt fetcher for latest-only data fetching
3. Build simplified orchestrator (single-run, no triple-median)
4. SQLite persistence (reports table)
5. FastAPI API routes (GET /reports, GET /reports/latest)
6. Minimal React frontend: dashboard showing latest report

### Phase 2: Scheduling & RRG
7. APScheduler daily 4:30 PM ET trigger
8. RRG quadrant math implementation
9. On-demand "Run Now" with 3/day rate limit
10. RRG scatter chart (Recharts)
11. Sector Scorecard view

### Phase 3: Narrative & History
12. Narrative generator agent (market story + per-sector WHY)
13. Analysis History browser (paginated list, click to detail)
14. Oversold detector (price vs fundamentals divergence)

### Rationale
- Phase 1 gets a working end-to-end prototype fast — data in, agent pipeline, results out, visible in browser
- Phase 2 adds the differentiating analytics (RRG) and automation (scheduler)
- Phase 3 adds the AI narrative polish and historical comparison

### Dependencies
- `ANTHROPIC_API_KEY` required for agent pipeline (all phases)
- `FRED_API_KEY` required for macro indicators (Phase 1, but can gracefully degrade)
- No external database — SQLite file is zero-config

---

## 7. External Research References

- [RRGPy — Python RRG implementation](https://github.com/An0n1mity/RRGPy)
- [RRG Sector Rotation India](https://github.com/AdroitAnandAI/RRG-Sector-Rotation-India)
- [StockCharts RRG ChartSchool](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts)
- [RRG Algorithm Gist](https://gist.github.com/tuhuynh27/c8abcf7f8469b7d91adac9a6947db64d)
- [Embedding React in FastAPI Monorepo](https://medium.com/@asafshakarzy/embedding-a-react-frontend-inside-a-fastapi-python-package-in-a-monorepo-c00f99e90471)
- [APScheduler + FastAPI Integration](https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186)
- [FastAPI Scheduling Guide](https://medium.com/@rasifrazak123/fastapi-scheduling-background-tasks-backgroundtasks-vs-apscheduler-vs-celery-complete-guide-ff90d6be524b)
- [FastAPI async SQLite (aiosqlite)](https://github.com/gordthompson/fastapi-tutorial-aiosqlite)
- [yfinance Rate Limiting Best Practices](https://www.slingacademy.com/article/rate-limiting-and-api-best-practices-for-yfinance/)
- [FastAPI Project Structure](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f)
