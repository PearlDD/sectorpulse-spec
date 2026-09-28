# Researcher Agent Output

- **timestamp:** 2026-08-07T18:39:44Z
- **exit_code:** 0

---

Research report written to `.factory/strategy/research.md`. Here's a summary of what it covers:

**Existing Code Reuse**: 4 files copy directly (config, macro_analyst, sector_analyst, portfolio_allocator) — all already follow the no-dates-in-prompts rule. The orchestrator and fetcher need adaptation (remove backtest logic, simplify to single-run).

**Key Findings**:
- **RRG is pure math** — no LLM needed. Double-smoothed WMA of relative strength vs SPY, normalized around 100. The "Improving" quadrant (RS-Ratio < 100, RS-Momentum > 100) directly maps to the Next-Hot Predictor feature.
- **APScheduler + FastAPI** integrates cleanly via `AsyncIOScheduler` + FastAPI's `lifespan` context manager with `CronTrigger(hour=16, minute=30, timezone="US/Eastern")`.
- **Monorepo structure**: FastAPI serves React's built `dist/` as static files, API routes under `/api/` prefix. Vite dev server proxies to FastAPI in development.
- **SQLite + aiosqlite** is sufficient — max ~4 writes/day, WAL mode handles concurrency.

**Top Pitfalls**: Switch from `claude-opus-4-6` to `claude-sonnet-4-6` (5-10x cheaper, sufficient for structured output). yfinance rate limits are low risk with only 12 tickers. FRED API should degrade gracefully if key is missing.

**MVP Phasing**: 3 phases — (1) core pipeline + minimal UI, (2) scheduler + RRG + scorecard, (3) narrative generation + history browser.
