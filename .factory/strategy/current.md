## Strategy — 2026-08-07

### Observations
- This is a greenfield build of SectorPulse — a full-stack web app wrapping an existing V2 sector rotation agent pipeline
- Source code exists at `/Users/pearl/factory-projects/sector-rotation-analytics-agent-vs-automation-arc/`
- 4 files copy directly: config.py, macro_analyst.py, sector_analyst.py, portfolio_allocator.py
- 2 files need adaptation: fetcher.py (remove backtest/ALFRED logic), orchestrator.py (single-run, add narrative step)
- New components: narrative generator, RRG math, oversold detector, SQLite persistence, scheduler, full React frontend
- All agent files already follow the no-dates critical rule — narrative generator must too
- Model should be switched from claude-opus-4-6 to claude-sonnet-4-6 for cost efficiency

### Hypotheses

#### H1: Project scaffold + eval harness
- **Category:** FIX
- **Type:** code
- **Backlog item:** Phase 1 scaffold
- **What:** Create the monorepo structure: `backend/` (FastAPI + pyproject.toml) and `frontend/` (React + Vite + TypeScript + Tailwind). Set up `factory.md`, basic eval harness, `.env.example`, and root README. Backend: `app/__init__.py`, `app/main.py` (FastAPI app with health endpoint), pyproject.toml with deps (fastapi, uvicorn, langchain-anthropic, yfinance, fredapi, apscheduler, aiosqlite, sqlalchemy[asyncio], pandas, numpy, pydantic). Frontend: `npm create vite@latest` with React+TS template, add tailwindcss and recharts. Vite proxy config pointing `/api` to FastAPI port 8000.
- **Why:** Everything depends on the project scaffold existing first
- **Expected impact:** Project becomes runnable — `uvicorn app.main:app` and `npm run dev` both work
- **Priority:** high

#### H2: Port config + data fetcher (adapted for latest-only)
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** Port reusable agent files and adapt fetcher early
- **What:** (1) Copy `config.py` → `backend/app/config.py`, removing backtest constants (START_DATE, END_DATE, TRANSACTION_COST_BPS, MAX_POSITIONS, SCORE_THRESHOLD, signal weights). Keep SECTOR_TICKERS, BENCHMARK_TICKER, SECTOR_LAUNCH_DATES, FRED_SERIES, FRED_SERIES_V2, CYCLE_SECTOR_MAP, get_available_sectors(). (2) Create `backend/app/data/fetcher.py` adapted from source: remove parquet storage dependency, remove ALFRED vintage logic, fetch "latest" data only (last 60 trading days for prices, latest values for FRED). FRED must degrade gracefully — if FRED_API_KEY missing, return empty macro dict with a logged warning instead of raising. Keep `_retry_with_backoff`. Return DataFrames/dicts directly. (3) Add helper `get_latest_macro_snapshot()` that returns a flat dict of latest indicator values (what agents consume).
- **Why:** Config and fetcher are foundational — agents and RRG both depend on them
- **Expected impact:** Data pipeline works end-to-end: prices and macro indicators fetchable
- **Priority:** high

#### H3: Port 3 agent files + switch to claude-sonnet-4-6
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** Port macro_analyst, sector_analyst, portfolio_allocator
- **What:** Copy the 3 agent files to `backend/app/agents/`. Changes: (1) Switch `ChatAnthropic(model="claude-opus-4-6")` → `ChatAnthropic(model="claude-sonnet-4-6")` in all 3 files. (2) Update imports from `src.config` → `app.config` and `src.agent_v2.agents.*` → `app.agents.*`. (3) Remove `decision_date` parameter from all function signatures — it was only kept for backtest API compat. The agents never pass it to the LLM (verified in source). (4) Keep all Pydantic models, prompts, and `_enforce_constraints` logic unchanged. (5) Add `__init__.py` re-exporting the models (CyclePhase, SectorAnalysis, SectorScore, PortfolioAllocation).
- **Why:** These 3 files are already production-quality and date-safe — minimal changes needed
- **Expected impact:** Agent pipeline callable from Python with correct structured output
- **Priority:** high

#### H4: RRG quadrant math + oversold detector
- **Category:** EXPLORE
- **Type:** code
- **Backlog item:** RRG quadrant model and oversold detector
- **What:** (1) Create `backend/app/data/rrg.py`: implement JdK RS-Ratio and RS-Momentum using double-smoothed WMA (window=10). Input: sector prices DataFrame + SPY benchmark. Output: per-sector dict with `rs_ratio`, `rs_momentum`, `quadrant` (Leading/Weakening/Lagging/Improving), and `trail` (last 5 data points for RRG chart animation). (2) Create `backend/app/data/oversold.py`: compare price momentum (negative 1m/3m return) against fundamental indicators (sector's cycle alignment score > 60) to flag divergences. Output: list of sectors with `ticker`, `price_momentum`, `fundamental_score`, `divergence_signal` (boolean). Pure math, no LLM calls.
- **Why:** RRG is the "Next-Hot Predictor" differentiator. Oversold detector finds price-vs-fundamentals divergences. Both are pure computation.
- **Expected impact:** Two key analytical features functional without any API costs
- **Priority:** high

#### H5: SQLite persistence layer
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** SQLite report storage
- **What:** Create `backend/app/db/` package: (1) `database.py` — async SQLAlchemy engine using `sqlite+aiosqlite:///data/sectorpulse.db`, WAL mode pragma, async session factory. (2) `models.py` — `Report` model with columns: id (PK), created_at (timestamp), trigger (scheduled/manual), cycle_phase, cycle_confidence, risk_level, narrative (text), sector_scores (JSON), allocation (JSON), rrg_data (JSON), raw_macro_data (JSON). (3) `crud.py` — async functions: `create_report()`, `get_reports(limit, offset)`, `get_latest_report()`, `get_report_by_id()`. (4) Auto-create tables on app startup via `Base.metadata.create_all`.
- **Why:** Reports need persistence for history browsing and the analysis history feature
- **Expected impact:** Reports stored and queryable; foundation for API routes
- **Priority:** high

#### H6: Adapted orchestrator + narrative generator
- **Category:** EXPLORE
- **Type:** code
- **Backlog item:** Adapt orchestrator for web app + new narrative generator
- **What:** (1) Create `backend/app/agents/narrative_gen.py` — new Claude agent that takes CyclePhase + SectorAnalysis + PortfolioAllocation and generates: `market_narrative` (2-3 paragraph macro story), `sector_explanations` (dict of ticker → WHY explanation). Uses claude-sonnet-4-6. Prompt must follow the no-dates critical rule: pass only numerical values and phase labels, never dates. Prompt should explicitly instruct: "Do not reference any specific dates, months, quarters, or years." (2) Create `backend/app/agents/orchestrator.py` — adapted from source: remove LangGraph dependency (use simple sequential calls), remove triple-run median (single run), remove BacktestState. New flow: fetch data → macro_analyst.analyze() → sector_analyst.analyze() → portfolio_allocator.allocate() → narrative_gen.generate() → compute RRG → detect oversold → return complete AnalysisResult (Pydantic model bundling all outputs). Accept a `trigger` param ("scheduled"/"manual").
- **Why:** Orchestrator is the backbone. Narrative generator is the key new feature that makes reports human-readable. Single-run saves 2/3 API cost.
- **Expected impact:** Full analysis pipeline runnable end-to-end producing a complete report
- **Priority:** high

#### H7: FastAPI API routes
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** REST API endpoints
- **What:** Create `backend/app/api/routes.py` with endpoints: (1) `GET /api/health` — returns status + last run timestamp. (2) `GET /api/reports` — paginated report list (query params: limit, offset), returns summary fields (id, created_at, cycle_phase, risk_level). (3) `GET /api/reports/latest` — most recent report with full data. (4) `GET /api/reports/{id}` — single report by ID, 404 if not found. (5) `POST /api/run` — trigger on-demand analysis, rate-limited to 3/day using in-memory counter (resets at midnight ET). Returns the new report. Runs orchestrator in background task, returns 202 with report ID. (6) `GET /api/sectors` — latest sector scorecard (scores + allocations). (7) `GET /api/sectors/rrg` — latest RRG data (rs_ratio, rs_momentum, quadrant per sector). Register router in main.py. Add CORS middleware for dev (localhost:5173).
- **Why:** Frontend needs these endpoints to display data
- **Expected impact:** All data accessible via REST API
- **Priority:** high

#### H8: APScheduler daily run + lifespan integration
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** Scheduled daily analysis at 4:30 PM ET
- **What:** Create `backend/app/scheduler.py`: (1) Set up AsyncIOScheduler with CronTrigger(hour=16, minute=30, timezone="US/Eastern") calling orchestrator.run() with trigger="scheduled". (2) Integrate via FastAPI lifespan context manager — start scheduler on startup, shutdown on app close. (3) Add `GET /api/schedule` endpoint returning next run time and last run status. (4) Make scheduler conditional — only starts if ANTHROPIC_API_KEY is set (no point scheduling if Claude can't be called).
- **Why:** Automated daily analysis is a core feature — runs after market close when data is freshest
- **Expected impact:** Hands-free daily report generation
- **Priority:** medium

#### H9: Frontend — app shell + dashboard page
- **Category:** EXPLORE
- **Type:** code
- **Backlog item:** React frontend — dashboard
- **What:** (1) Set up React Router with nav layout (sidebar or top nav): Dashboard, RRG Chart, History pages. (2) Create `src/api/client.ts` — typed fetch wrapper for all `/api/*` endpoints with error handling. (3) Create `Dashboard.tsx` — "Hot Sectors" view: top-5 allocated sectors as cards showing ticker, score, weight, and AI-generated WHY explanation (from narrative). Market cycle banner at top showing phase + confidence + risk level. Narrative panel showing the full market story. Use Tailwind for styling — dark theme with sector-colored accents. (4) Create `RunButton.tsx` — "Run Now" button that POSTs to `/api/run`, shows loading state, disables when rate limit hit (3/day), displays remaining runs count.
- **Why:** Dashboard is the primary user-facing view — shows the actionable output
- **Expected impact:** Users can see analysis results and trigger on-demand runs
- **Priority:** high

#### H10: Frontend — RRG chart page
- **Category:** EXPLORE
- **Type:** code
- **Backlog item:** RRG scatter plot visualization
- **What:** Create `RRGChart.tsx` page with Recharts ScatterChart: (1) X-axis = RS-Ratio (centered at 100), Y-axis = RS-Momentum (centered at 100). (2) Four quadrants labeled: Leading (top-right, green), Weakening (bottom-right, yellow), Lagging (bottom-left, red), Improving (top-left, blue). Draw quadrant lines at x=100 and y=100. (3) Each sector plotted as a labeled dot with its ticker. (4) Trail lines showing last 5 data points (trajectory). (5) Tooltip on hover showing sector name, exact RS-Ratio/Momentum values, and quadrant. (6) "Improving" quadrant sectors highlighted with a callout — these are the Next-Hot candidates. (7) Fetch data from `GET /api/sectors/rrg`.
- **Why:** RRG chart is the signature visualization for sector rotation — the "Next-Hot Predictor" feature
- **Expected impact:** Visual identification of sector rotation dynamics
- **Priority:** high

#### H11: Frontend — sector scorecard + history browser
- **Category:** EXPLORE
- **Type:** code
- **Backlog item:** Sector scorecard and analysis history
- **What:** (1) Create `SectorScorecard.tsx` — table/grid of all 11 sectors showing: ticker, name, score (0-100 with color gradient), allocation weight (if in portfolio), RRG quadrant badge, 1m/3m momentum arrows, oversold flag. Sortable by score. Fetches from `GET /api/sectors`. (2) Create `History.tsx` — paginated list of past reports showing date, cycle phase, risk level, top-3 sectors. Click navigates to detail. Infinite scroll or pagination. Fetches from `GET /api/reports`. (3) Create `Report.tsx` — single report detail view showing full narrative, sector scores, allocation pie chart (Recharts PieChart), and RRG snapshot. Fetches from `GET /api/reports/{id}`.
- **Why:** Scorecard gives the at-a-glance view, history enables temporal comparison
- **Expected impact:** Complete frontend feature set
- **Priority:** medium

#### H12: Static serving + production build + integration tests
- **Category:** EXPLOIT
- **Type:** code
- **Backlog item:** Production deployment setup
- **What:** (1) Update `backend/app/main.py` to mount `frontend/dist/` as StaticFiles with `html=True` for SPA fallback — only if the dist directory exists (dev mode skips this). API routes under `/api/` prefix take priority over static catch-all. (2) Add `build.sh` script: `cd frontend && npm run build && cd ..` (3) Add integration test in `backend/tests/test_api.py` using httpx AsyncClient: test health endpoint, test reports CRUD with a test SQLite DB, test rate limiting on /api/run (mock the orchestrator to avoid Claude calls). (4) Add `.env.example` with ANTHROPIC_API_KEY, FRED_API_KEY (optional), and comments explaining each. (5) Unit tests for RRG math (known inputs → expected quadrants) and oversold detector.
- **Why:** Production serving, testing, and developer onboarding essentials
- **Expected impact:** App deployable as single process, core logic tested
- **Priority:** medium

### Anti-patterns to Avoid
- Do NOT use triple-run median from source orchestrator — single run for cost efficiency
- Do NOT pass dates to any agent prompts — critical anti-look-ahead-bias rule
- Do NOT use claude-opus-4-6 — switch all agents to claude-sonnet-4-6
- Do NOT use LangGraph for the web orchestrator — overkill for a linear sequential pipeline, use simple async function calls
- Do NOT use parquet storage from source fetcher — SQLite is the persistence layer
- Do NOT raise errors on missing FRED_API_KEY — degrade gracefully with a warning

### Dependency Graph

```
H1 (scaffold)
├── H2 (config + fetcher)
│   ├── H3 (agents)
│   │   └── H6 (orchestrator + narrative)
│   │       ├── H7 (API routes)
│   │       │   ├── H8 (scheduler)
│   │       │   ├── H9 (dashboard)
│   │       │   ├── H10 (RRG chart)
│   │       │   └── H11 (scorecard + history)
│   │       └── H12 (static serving + tests)
│   └── H4 (RRG math + oversold)
│       └── H6 (orchestrator uses RRG + oversold)
└── H5 (SQLite layer)
    └── H7 (API routes use DB)
```

### Build Order (respecting dependencies)

| Phase | Issues | Can Parallelize |
|-------|--------|-----------------|
| 1 | H1 | — |
| 2 | H2, H5 | Yes (independent) |
| 3 | H3, H4 | Yes (independent, both depend on H2) |
| 4 | H6 | Depends on H3, H4 |
| 5 | H7 | Depends on H5, H6 |
| 6 | H8, H9, H10, H11 | Yes (all depend on H7) |
| 7 | H12 | Depends on H7, frontend phases |

## Deferred

- **ANTHROPIC_API_KEY** — user must provide their Anthropic API key. Required for all agent pipeline functionality (macro analyst, sector analyst, portfolio allocator, narrative generator). Set in `.env` file. Without this key, no analysis can run.
- **FRED_API_KEY** — user must register for a free key at https://fred.stlouisfed.org/docs/api/api_key.html and set it in `.env`. Without this key, macro indicators (PMI, yield curve, credit spreads, VIX) will be unavailable and analysis quality will be reduced. The app degrades gracefully — RRG and price-based analysis still work.
