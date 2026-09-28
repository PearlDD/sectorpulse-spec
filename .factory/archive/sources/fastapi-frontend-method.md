---
tags:
  - factory
  - source
  - sectorpulse
source: factory-archivist
date: 2026-08-07
---

# FastAPI `app.frontend()` Method (v0.138.0+)

## Finding

FastAPI 0.138.0 (released June 2026) introduced native SPA support via `app.frontend()`:

```python
app.frontend("/", directory=str(_frontend_dist), fallback="index.html")
```

Key behaviors:
- Serves static assets normally (JS, CSS, images)
- Falls back to `index.html` for GET/HEAD requests accepting HTML
- Missing static assets still return 404
- API path operations always take priority regardless of call order
- `fallback="auto"` (default) auto-detects `index.html` if present

## Applicability to SectorPulse

**Not currently usable.** The project has FastAPI 0.115.0 installed and `pyproject.toml` is read-only per factory scope rules. This is the preferred solution for future projects or if the version constraint is lifted.

## Reference

- [FastAPI app.frontend() Explained](https://umesh-malik.com/blog/fastapi-spa-app-frontend-explained)
- [FastAPI Frontend Tutorial (official docs)](https://fastapi.tiangolo.com/tutorial/frontend/)
