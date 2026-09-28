---
tags:
  - factory
  - project
  - sectorpulse-spec
source: factory-archivist
---

# Factory: sectorpulse-spec

## Status
- **State**: COMPLETE
- **Current Score**: N/A (greenfield build, no scoring)
- **Experiments Run**: 12
- **Kept**: 12, **Reverted**: 0
- **Build Plan**: 12 hypotheses across 7 phases — ALL COMPLETE

## Project Overview
SectorPulse is a full-stack web app (FastAPI + React/Vite) wrapping an existing V2 sector rotation agent pipeline. Provides AI-driven sector rotation analytics via browser UI with scheduled daily runs, historical report storage, on-demand analysis, and RRG charts.

## Build Progress

### Phase 1 — COMPLETE (2026-08-07)
- **H1: Project scaffold + eval harness** — KEEP
  - Commit: `dfc6d4b`
  - Backend: FastAPI app, health endpoint, all module packages
  - Frontend: React+TS+Tailwind+Recharts, Vite proxy to :8000
  - Root: .env.example, .gitignore, CLAUDE.md, eval harness
  - CEO verdict: PROCEED, zero issues

### Phase 2 — COMPLETE (2026-08-07)
- **H2: Port config + data fetcher (adapted for latest-only)** — KEEP
  - Commit: `964e678`
  - Config ported (backtest constants removed), latest-only fetcher with graceful FRED degradation
  - 12 tests passing
  - CEO verdict: PROCEED, zero issues
- **H5: SQLite persistence layer** — KEEP
  - Commit: `b7b9033`
  - Async SQLAlchemy + aiosqlite, WAL mode, Report model, CRUD operations
  - 7 tests passing
  - CEO verdict: PROCEED, zero issues

### Phase 3 — COMPLETE (2026-08-07)
- **H3: Port 3 agent files + switch to claude-sonnet-4-6** — KEEP
  - Commit: `71f3cf4`
  - Ported macro_analyst, sector_analyst, portfolio_allocator
  - Model switch opus->sonnet, import updates, decision_date removal
  - 10 tests passing including date-safety checks
  - CEO verdict: PROCEED, zero issues
- **H4: RRG quadrant math + oversold detector** — KEEP
  - Commit: `c5e150c`
  - JdK RS-Ratio/RS-Momentum with double-smoothed WMA, quadrant classification
  - Oversold detector: price momentum vs fundamental divergence
  - 20 tests passing
  - CEO verdict: PROCEED, zero issues

### Phase 4 — COMPLETE (2026-08-07)
- **H6: Orchestrator + narrative generator** — KEEP
  - Commit: `418f03e`
  - Sequential pipeline orchestrator (no LangGraph), narrative generator (no-dates rule)
  - AnalysisResult bundles all outputs, error handling at each stage
  - 63 total tests passing
  - CEO verdict: PROCEED, zero issues

### Phase 5 — COMPLETE (2026-08-07)
- **H7: FastAPI API routes with CORS and rate limiting** — KEEP
  - Commit: `14ed502`
  - 7 REST endpoints, CORS middleware, rate limiting with midnight ET reset
  - 76 total tests passing
  - CEO verdict: PROCEED, zero issues

### Phase 6 — COMPLETE (2026-08-07)
- **H8: APScheduler daily run + lifespan integration** — KEEP
  - Commit: `e72b735`
  - APScheduler with daily trigger, conditional startup, lifespan integration
  - CEO verdict: PROCEED, zero issues
- **H9: App shell, API client, and dashboard** — KEEP
  - Commit: `9fa7dd6`
  - React app shell with nav, typed API client, dashboard with hot sectors + narrative + run button
  - 385 lines of frontend code
  - CEO verdict: PROCEED, zero issues
- **H10: RRG chart page with quadrant visualization** — KEEP
  - Commit: `3d1f199`
  - Four-quadrant RRG chart, sector trails, improving callouts
  - 300 lines
  - CEO verdict: PROCEED, zero issues
- **H11: Sector scorecard, history browser, report detail** — KEEP
  - Commit: `0aa1b61`
  - Scorecard table, history browser, report detail with pie chart
  - 597 lines across 5 files
  - CEO verdict: PROCEED, zero issues

### Phase 7 — COMPLETE (2026-08-07)
- **H12: Static serving + build script + integration tests** — KEEP
  - Commit: `8dfee01`
  - StaticFiles mount with SPA fallback (conditional, after API routes)
  - 6 integration tests (170 lines), build.sh
  - 88 total tests passing
  - CEO verdict: PROCEED, zero issues

## Test Summary
- H1: scaffold passing
- H2: 12 tests
- H3: 10 tests (incl. date-safety)
- H4: 20 tests
- H5: 7 tests
- H6: ~14 tests (63 total - 49 prior)
- H7: ~13 tests (76 total - 63 prior)
- H8: scheduler tests added
- H12: 6 integration tests added
- **Total: 88 tests, all passing; frontend compiles clean**

## Research Summary (2026-08-07)
- 4 agent files copy from existing repo, 2 need adaptation
- RRG algorithm is pure math, no LLM needed
- Architecture: FastAPI monorepo serving React static files
- Key constraints: no dates in prompts, graceful FRED degradation, sonnet not opus, no LangGraph

## Strategy
- See: strategies/sectorpulse-spec-2026-08-07.md

## Cycle Summary (2026-08-07)
- **Build Cycle**: Complete greenfield build in single session
- **Hypotheses**: 12/12 KEPT, 0 reverted — 100% keep rate
- **Total Tests**: 88 (all passing)
- **Frontend**: Compiles clean, 0 warnings
- **Factory Baseline**: Initialized at 0.60 score via `eval/run_eval.py`
- **Commits**: 13 total (12 hypotheses + 1 factory init)
- **Key Constraints Enforced**: No dates in agent prompts, claude-sonnet-4-6 (not opus), graceful FRED degradation, no LangGraph
- **Architecture**: FastAPI monorepo serving React static files, SQLite WAL persistence, APScheduler daily runs
- **Outcome**: Production-ready MVP — all 8 spec features implemented, tested, and integrated

## Recent Experiments
- H12 — Static serving + build script + integration tests (KEEP, 2026-08-07) **FINAL**
- H11 — Sector scorecard, history browser, report detail (KEEP, 2026-08-07)
- H10 — RRG chart with quadrant visualization (KEEP, 2026-08-07)
- H9 — App shell, API client, dashboard (KEEP, 2026-08-07)
- H8 — APScheduler daily run + lifespan (KEEP, 2026-08-07)
- H7 — FastAPI API routes + CORS + rate limiting (KEEP, 2026-08-07)
- H6 — Orchestrator + narrative generator (KEEP, 2026-08-07)
- H4 — RRG quadrant math + oversold detector (KEEP, 2026-08-07)
- H3 — Port 3 agent files + switch to sonnet (KEEP, 2026-08-07)
- H5 — SQLite persistence layer (KEEP, 2026-08-07)
- H2 — Port config + data fetcher (KEEP, 2026-08-07)
- H1 — Project scaffold + eval harness (KEEP, 2026-08-07)
