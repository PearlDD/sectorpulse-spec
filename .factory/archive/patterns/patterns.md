---
tags:
  - factory
  - patterns
source: factory-archivist
---

# Cross-Project Patterns

## Clean Greenfield Builds with Zero Reverts
Observed in sectorpulse-spec (H1–H11): 11 consecutive KEEP verdicts with zero reverts across 6 phases. Contributing factors: thorough upfront research phase producing 5 source notes, phased build plan with dependency ordering, and strong test coverage at each step (76+ tests by Phase 6). Pattern: investing in research and strategy before building pays off in zero-rework builds.

## Backend-First Then Frontend Batch
Observed in sectorpulse-spec Phase 6 (H8–H11): batching all 4 frontend pages into a single phase after the full backend was complete (API, scheduler, persistence) resulted in clean compilation with no API integration issues. The typed API client (H9) established contracts once, and subsequent pages (H10, H11) reused it without changes. Pattern: completing the API surface before starting frontend work eliminates integration churn.

## Perfect 12/12 Keep Rate in Single-Day Greenfield
Observed in sectorpulse-spec (H1–H12): all 12 hypotheses kept across 7 phases in a single day, 88 tests passing, zero reverts. Contributing factors: (1) detailed research phase with 5 source notes before any code, (2) dependency-ordered phasing so each hypothesis built on stable foundations, (3) integration tests added at the final phase to validate the full stack. Pattern: for greenfield projects with clear specs, front-loading research and strict phase ordering can yield 100% keep rates.

## Finalize Gate Override Friction on Infrastructure Fixes
Observed in sectorpulse experiment #1–#3: infra bug fixes (SPA static serving) with near-zero score delta triggered finalize gate precheck failures (score_direction, anti_pattern) even when the CEO kept the experiment. Required 3 attempts before manual_pass override succeeded. Pattern: infrastructure/routing fixes that don't directly improve scored functionality may need manual precheck bypass. The gate's score_direction check penalizes correct fixes that have minimal score impact.
