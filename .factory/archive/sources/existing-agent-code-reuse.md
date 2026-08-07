---
tags:
  - factory
  - source
  - sectorpulse-spec
source: factory-archivist
date: 2026-08-07
---

# Existing Agent Code Reuse Analysis

## Findings

The V2 sector rotation agent pipeline in `sector-rotation-analytics-agent-vs-automation-arc` contains reusable components for SectorPulse:

### Copy As-Is (4 files)
- `src/config.py` — SECTOR_TICKERS, FRED_SERIES, CYCLE_SECTOR_MAP, get_available_sectors(). Remove backtest-specific constants.
- `src/agent_v2/agents/macro_analyst.py` — CyclePhase model + analyze(). Already date-free.
- `src/agent_v2/agents/sector_analyst.py` — SectorAnalysis/SectorScore models + analyze(). Already date-free.
- `src/agent_v2/agents/portfolio_allocator.py` — PortfolioAllocation model + allocate(). Already date-free.

### Needs Adaptation (2 files)
- `src/agent_v2/orchestrator.py` — Heavy adaptation. Remove triple-run median, BacktestState. Add single-run mode + narrative generation step.
- `src/data/fetcher.py` — Moderate adaptation. Remove ALFRED vintage logic. Keep fetch_sector_prices() and fetch_macro_indicators(). Fetch "latest" only.

### New Components Needed
- Narrative generator agent (Claude call for market story + per-sector WHY)
- RRG quadrant classifier (pure math, no LLM)
- Oversold detector (price vs fundamental divergence)
- SQLite persistence layer
- APScheduler integration (daily 4:30 PM ET)
- Full React frontend
