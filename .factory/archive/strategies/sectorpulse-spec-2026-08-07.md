---
tags:
  - factory
  - strategy
  - sectorpulse-spec
date: 2026-08-07
source: factory-archivist
---

# Strategy: sectorpulse-spec — 2026-08-07

## CEO Verdict: PROCEED

Plan approved with no issues. 12 hypotheses across 7 build phases with clear dependency graph.

## Build Plan (12 Hypotheses)

| Phase | Hypotheses | Description | Parallel |
|-------|-----------|-------------|----------|
| 1 | H1 | Project scaffold + eval harness | — |
| 2 | H2, H5 | Config+fetcher + SQLite layer | Yes |
| 3 | H3, H4 | Port 3 agents + RRG math/oversold detector | Yes |
| 4 | H6 | Orchestrator + narrative generator | — |
| 5 | H7 | FastAPI API routes | — |
| 6 | H8, H9, H10, H11 | Scheduler + all frontend pages | Yes |
| 7 | H12 | Static serving + integration tests | — |

## Key Decisions

- **Model**: claude-sonnet-4-6 (not opus) for cost efficiency
- **Orchestration**: Simple sequential async calls (no LangGraph)
- **Pipeline**: Single-run analysis (no triple-run median)
- **Persistence**: SQLite with WAL mode + aiosqlite
- **Scheduler**: APScheduler, daily at 4:30 PM ET
- **Frontend**: React + Vite + TypeScript + Tailwind + Recharts
- **Serving**: FastAPI mounts frontend/dist/ as static files in production

## Anti-Patterns (Must Avoid)

- No dates in agent prompts (anti-look-ahead-bias rule)
- No exceptions on missing FRED_API_KEY (graceful degradation)
- No parquet storage (use SQLite)
- No triple-run median (single run for cost)

## CEO Notes for Builder

- Copy agent files from `/Users/pearl/factory-projects/sector-rotation-analytics-agent-vs-automation-arc/`
- Switch all Claude model refs to claude-sonnet-4-6
- Narrative generator prompt MUST NOT contain dates
- FRED API must degrade gracefully

## Deferred (Requires Human)

- ANTHROPIC_API_KEY — required for all agent functionality
- FRED_API_KEY — optional, macro indicators unavailable without it
