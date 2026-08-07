---
tags:
  - factory
  - experiment
  - sectorpulse
project: sectorpulse
experiment_id: 1
verdict: PENDING (CEO: PROCEED)
score_delta: pending post-change eval
date: 2026-08-07
source: factory-archivist
---

# Experiment #1: Fix SPA static serving with SPAStaticFiles fallback

## Hypothesis
Add `lookup_path` override to serve `index.html` for SPA client-side routes — browsing to `/dashboard`, `/rrg`, `/history`, `/report/:id` on the FastAPI server should load the React app instead of returning 404.

## Result
**CEO VERDICT: PROCEED** — PR #5 implements exactly what was requested. Builder modified only `backend/app/main.py`. 87 tests pass. Awaiting post-change eval for score delta.

## What Changed (PR #5, commit 997d093)

### `backend/app/main.py` — sole file modified
1. **`SPAStaticFiles` subclass** — overrides `lookup_path()` to fall back to `index.html` when the requested path doesn't match a real static file. This gives SPA client-side routing support.
2. **`dotenv` loading** — added `load_dotenv()` at module top (before FastAPI imports) with `# noqa: E402` comments for the post-dotenv imports.
3. **Mount swap** — replaced `StaticFiles` with `SPAStaticFiles` in the `app.mount("/", ...)` call.
4. **`_frontend_dist`** moved to module level (was inline at mount site).

### Implementation detail
- `lookup_path` is synchronous in Starlette 0.38.6 (the project's pinned version) — Builder correctly used sync signature `def lookup_path(self, path: str) -> Tuple[str, Optional[os.stat_result]]`.
- Fallback returns `super().lookup_path("./index.html")` — relative path ensures it resolves within the mounted directory.

## CEO Review
- **Verdict:** PROCEED
- **Issues found:** None
- **Rationale:** No scope creep, no test deletions, implementation matches approved strategy (Option B from research).
- **Next step:** Reviewer verify guard compliance, then post-change eval.

## Links
- Project: sectorpulse
- PR: #5
- Branch: experiment/1-spa-static-fallback
- Commit: 997d093
- Strategy: [strategies/sectorpulse-2026-08-07.md](../strategies/sectorpulse-2026-08-07.md)
- Research: [sources/spa-static-serving-fastapi.md](../sources/spa-static-serving-fastapi.md)
