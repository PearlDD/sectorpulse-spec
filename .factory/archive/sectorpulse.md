---
tags:
  - factory
  - project
  - sectorpulse
source: factory-archivist
---

# Factory: sectorpulse

## Status
- **State**: experiment-in-progress (awaiting post-change eval)
- **Current Score**: 0.6069 (baseline)
- **Experiments Run**: 1
- **Kept**: 0 (pending), **Reverted**: 0

## Current Focus
Experiment 1 — SPA static fallback fix. Builder PR #5 merged to experiment branch. CEO verdict: PROCEED. Awaiting reviewer + post-change eval.

## Research Summary (2026-08-07)
- Root cause identified: `StaticFiles(html=True)` does not provide SPA catch-all fallback
- Recommended approach: SPAStaticFiles subclass with `lookup_path` override (Option B)
- Option A (`app.frontend()`) rejected — requires FastAPI >=0.138, project has 0.115 and pyproject.toml is read-only
- Only `backend/app/main.py` needs modification

## Recent Experiments
- Experiment #1 — SPA static serving with SPAStaticFiles fallback (CEO: PROCEED, pending eval)
  - PR #5, commit 997d093, branch: experiment/1-spa-static-fallback
  - [Experiment note](experiments/sectorpulse-001.md)
