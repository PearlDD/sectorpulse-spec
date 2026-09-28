---
tags:
  - factory
  - project
  - sectorpulse
source: factory-archivist
---

# Factory: sectorpulse

## Status
- **State**: idle (cycle complete)
- **Current Score**: 0.6293
- **Experiments Run**: 3 (plus 12 prior greenfield hypotheses H1–H12)
- **Kept**: 1, **Reverted**: 2 (gate overrides)

## Current Focus
Cycle complete. PR #6 open for human review. Backlog item "Fix frontend static serving" cleared.

## Cycle Summary (2026-08-07)

### Problem
SPA client-side routes (`/dashboard`, `/rrg`, etc.) returned 404 when accessed directly on the FastAPI server. `StaticFiles(html=True)` does not provide SPA catch-all fallback.

### Solution
`SPAStaticFiles` subclass with `lookup_path` override in `backend/app/main.py`. Falls back to `index.html` for unmatched paths, enabling React Router to handle client-side routing.

### Outcome
Score improved from 0.6292 to 0.6293 (+0.0001). Fix is minimal (single file change), e2e tests pass, 87+ tests green.

### Gate Friction
Experiments 1 and 2 were overridden to revert by the finalize gate despite CEO keep decisions, due to score_direction and anti_pattern precheck failures. Experiment 3 passed after manual precheck verification.

## Research Summary (2026-08-07)
- Root cause identified: `StaticFiles(html=True)` does not provide SPA catch-all fallback
- Recommended approach: SPAStaticFiles subclass with `lookup_path` override (Option B)
- Option A (`app.frontend()`) rejected — requires FastAPI >=0.138, project has 0.115 and pyproject.toml is read-only
- Only `backend/app/main.py` needs modification

## Recent Experiments
- Experiment #1 — SPA static fallback (REVERT — gate override, score_direction precheck)
  - [Experiment note](experiments/sectorpulse-001.md)
- Experiment #2 — SPA static fallback retry (REVERT — gate override, score_direction + anti_pattern)
- Experiment #3 — SPAStaticFiles with lookup_path override (**KEEP**, +0.0001)
  - PR #6, branch: experiment/2-spa-static-fallback
  - [Experiment note](experiments/sectorpulse-003.md)
