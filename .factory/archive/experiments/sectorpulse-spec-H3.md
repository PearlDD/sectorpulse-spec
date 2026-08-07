---
tags:
  - factory
  - experiment
  - sectorpulse-spec
project: sectorpulse-spec
experiment_id: H3
verdict: KEEP
score_delta: N/A
date: 2026-08-07
source: factory-archivist
---

# Experiment H3: Port 3 agent files + switch to claude-sonnet-4-6

## Hypothesis
Copy macro_analyst, sector_analyst, and portfolio_allocator from existing repo. Switch model from claude-opus-4-6 to claude-sonnet-4-6, update imports, remove decision_date parameter.

## Result
**KEEP** — CEO verdict: PROCEED, zero issues found.

## What Changed
- Ported 3 agent files to `backend/app/agents/`
- Switched `ChatAnthropic(model="claude-opus-4-6")` to `claude-sonnet-4-6` in all files
- Updated imports from `src.config` / `src.agent_v2.agents.*` to `app.config` / `app.agents.*`
- Removed `decision_date` parameter from all function signatures (backtest-only artifact)
- Kept all Pydantic models, prompts, and `_enforce_constraints` logic unchanged
- Added `__init__.py` re-exporting models (CyclePhase, SectorAnalysis, SectorScore, PortfolioAllocation)
- 10 tests passing including date-safety checks
- Commit: `71f3cf4`

## Links
- Project: sectorpulse-spec
- Commit: 71f3cf4
- Phase: 3 (parallel with H4)
