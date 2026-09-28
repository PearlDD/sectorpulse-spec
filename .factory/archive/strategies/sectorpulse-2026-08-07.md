---
tags:
  - factory
  - strategy
  - sectorpulse
date: 2026-08-07
source: factory-archivist
---

# Strategy: sectorpulse — 2026-08-07

## CEO Verdict: PROCEED

The CEO approved the Strategist's plan with no issues found.

## Hypothesis: H1 — Fix frontend static serving with SPAStaticFiles fallback

- **Category:** FIX
- **Priority:** High
- **Target file:** `backend/app/main.py`

### What
Add an `SPAStaticFiles` class that subclasses `StaticFiles` and overrides `lookup_path` to fall back to `index.html` when a path is not found. Mount at `/` after all API routes. Also add `dotenv` loading.

### Why
Current `main.py` is a bare skeleton with only `/api/health`. Browsing to `localhost:8000` returns 404. The SPA needs all non-API routes to serve `index.html` so React Router handles client-side navigation. The `lookup_path` override is the established pattern for FastAPI < 0.138.

### Key Implementation Details
1. Define `SPAStaticFiles(StaticFiles)` with `lookup_path` override
2. Compute frontend dist path: `Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"`
3. Conditionally mount only if `_frontend_dist.is_dir()`
4. Mount MUST come after all `app.include_router()` and `@app.get()` declarations
5. Add `dotenv` loading at module level

### Anti-patterns to Avoid
- Do NOT use `app.frontend()` (requires FastAPI >= 0.138, project has 0.115.0)
- Do NOT modify `pyproject.toml` (read-only)
- Do NOT use catch-all route `@app.get("/{path:path}")` (conflicts with StaticFiles)

### Expected Impact
- pytest FAIL → PASS
- Frontend becomes accessible at all client-side routes
- API routes (`/api/health`, etc.) continue to work

### CEO Notes
Builder should implement the full `main.py` (routes, middleware, lifespan, scheduler, static serving with SPA fallback) since the main branch version is a skeleton.
