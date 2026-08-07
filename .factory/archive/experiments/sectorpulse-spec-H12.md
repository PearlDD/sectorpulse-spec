---
tags:
  - factory
  - experiment
  - sectorpulse-spec
project: sectorpulse-spec
experiment_id: H12
verdict: KEEP
score_delta: N/A
date: 2026-08-07
source: factory-archivist
---

# Experiment #H12: Static serving, build script, and integration tests

## Hypothesis
Add static file serving for the React frontend (SPA fallback), a production build script, and integration tests covering the full API surface.

## Result
**KEEP** — 88 total tests pass. CEO verdict: PROCEED, zero issues. Final build phase complete.

## What Changed
- `backend/app/main.py` — Mount `frontend/dist/` as StaticFiles with SPA fallback (conditional on dist/ existing, placed after API routes)
- `backend/tests/test_integration.py` — 6 integration tests covering health, run, reports CRUD, and 404 cases (170 lines)
- `build.sh` — Frontend production build script (3 lines)
- 3 files changed, 181 insertions

## Notes
This is the final hypothesis (12/12). All 12 hypotheses across 7 phases were kept with zero reverts. The project is now feature-complete as specified.

## Links
- Project: sectorpulse-spec
- Commit: `8dfee01`
- Phase: 7 (final)
