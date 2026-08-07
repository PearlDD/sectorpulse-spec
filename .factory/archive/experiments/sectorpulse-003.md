---
tags:
  - factory
  - experiment
  - sectorpulse
project: sectorpulse
experiment_id: 3
verdict: keep
score_delta: +0.0001
date: 2026-08-07
source: factory-archivist
---

# Experiment #3: Add SPAStaticFiles class to serve React SPA for client-side routes

## Hypothesis
Add `SPAStaticFiles` class with `lookup_path` override so that SPA client-side routes (`/dashboard`, `/rrg`, `/history`, `/report/:id`) return `index.html` instead of 404.

## Result
**KEEP** — score changed from 0.6292 to 0.6293 (+0.0001)

## What Changed
- Added `SPAStaticFiles` subclass of `StaticFiles` in `backend/app/main.py`
- Overrides `lookup_path()` to fall back to `index.html` when the requested path doesn't match a real static file
- Replaced `StaticFiles` with `SPAStaticFiles` in `app.mount("/", ...)` call
- Implementation uses sync `lookup_path` signature matching Starlette 0.38.6

## Context
This experiment went through 3 iterations (experiments 1–3) due to finalize gate prechecks failing on experiments 1 and 2. Both were overridden to revert despite CEO keep decisions. Experiment 3 passed manual precheck verification and was kept.

- Experiment 1: CEO kept, gate overrode to revert (score_direction precheck failed)
- Experiment 2: CEO kept, gate overrode to revert (score_direction + anti_pattern precheck failed)
- Experiment 3: CEO kept, gate passed (manual_pass), **KEPT**

## Links
- Project: sectorpulse
- Issue: #4
- PR: #6
- Branch: experiment/2-spa-static-fallback
- Score: 0.6292 → 0.6293
