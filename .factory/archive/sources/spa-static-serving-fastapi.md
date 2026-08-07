---
tags:
  - factory
  - source
  - sectorpulse
source: factory-archivist
date: 2026-08-07
---

# SPA Static Serving in FastAPI — Root Cause & Solutions

## Finding

`StaticFiles(directory=..., html=True)` mounted at `/` only serves `index.html` for directory roots (`/`), not as a catch-all fallback for SPA client-side routes (`/dashboard`, `/rrg`, `/history`, `/report/:id`). For `/dashboard`, it looks for `frontend/dist/dashboard/index.html` — which doesn't exist — and returns 404.

## Solution Options Identified

### Option A: `app.frontend()` (FastAPI ≥0.138.0)
Native SPA support added in FastAPI 0.138.0 (June 2026). Automatically falls back to `index.html` for HTML-accepting GET/HEAD requests. API routes always take priority.

**CEO verdict: NOT viable** — FastAPI 0.115.0 is installed and `pyproject.toml` is read-only per factory scope rules.

### Option B: SPAStaticFiles Subclass (Selected)
Subclass `StaticFiles` and override `lookup_path` to fall back to `index.html` when no file is found:

```python
class SPAStaticFiles(StaticFiles):
    async def lookup_path(self, path):
        full_path, stat_result = await super().lookup_path(path)
        if stat_result is None:
            return await super().lookup_path("./index.html")
        return full_path, stat_result
```

Well-established community pattern, no version bump needed, only modifies `main.py`.

### Option C: Catch-All Route
Simple but fragile — conflicts with StaticFiles mount, doesn't serve assets, ordering-sensitive.

## References

- [FastAPI Frontend Tutorial](https://fastapi.tiangolo.com/tutorial/frontend/)
- [Serving SPAs from Starlette — SPAStaticFiles pattern](https://www.crccheck.com/blog/serving-spas-from-starlette/)
- [Serving React with FastAPI — SPAStaticFiles via get_response](https://davidmuraya.com/blog/serving-a-react-frontend-application-with-fastapi/)
- [Starlette StaticFiles docs](https://starlette.dev/staticfiles/)
- [Starlette Discussion #2116 — SPA 200.html support](https://github.com/Kludex/starlette/discussions/2116)
