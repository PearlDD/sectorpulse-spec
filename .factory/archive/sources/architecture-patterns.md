---
tags:
  - factory
  - source
  - sectorpulse-spec
source: factory-archivist
date: 2026-08-07
---

# Architecture Patterns — FastAPI + React Monorepo

## Findings

### Serving Strategy
- FastAPI serves built React app as static files from `frontend/dist/`
- Dev: Vite on port 5173, proxy to FastAPI on 8000
- Prod: `npm run build` → FastAPI mounts `StaticFiles(directory="frontend/dist", html=True)`
- API routes prefixed `/api/` to avoid SPA catch-all conflict

### API Design
- GET /api/reports — paginated list
- GET /api/reports/latest — most recent
- GET /api/reports/{id} — single report
- POST /api/run — on-demand analysis (rate-limited 3/day)
- GET /api/sectors — current scorecard
- GET /api/sectors/rrg — RRG data
- GET /api/health — health check

### Database
- SQLite with WAL mode for concurrent reads during writes
- aiosqlite via SQLAlchemy async engine
- Single `reports` table with JSON columns for sector_scores, allocation, rrg_data, raw_macro_data

### Scheduler
- APScheduler AsyncIOScheduler with CronTrigger(hour=16, minute=30, timezone="US/Eastern")
- Integrated via FastAPI lifespan context manager

### References
- [Embedding React in FastAPI Monorepo](https://medium.com/@asafshakarzy/embedding-a-react-frontend-inside-a-fastapi-python-package-in-a-monorepo-c00f99e90471)
- [APScheduler + FastAPI](https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186)
- [FastAPI async SQLite](https://github.com/gordthompson/fastapi-tutorial-aiosqlite)
- [FastAPI Project Structure](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f)
