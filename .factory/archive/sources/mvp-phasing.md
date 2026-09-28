---
tags:
  - factory
  - source
  - sectorpulse-spec
source: factory-archivist
date: 2026-08-07
---

# MVP Phasing Recommendation

## Findings

### Phase 1: Core Pipeline (build first)
1. Port 4 reusable agent files (macro_analyst, sector_analyst, portfolio_allocator, config)
2. Adapt fetcher for latest-only data
3. Simplified orchestrator (single-run, no triple-median)
4. SQLite persistence (reports table)
5. FastAPI API routes (GET /reports, GET /reports/latest)
6. Minimal React frontend: dashboard showing latest report

### Phase 2: Scheduling & RRG
7. APScheduler daily 4:30 PM ET trigger
8. RRG quadrant math implementation
9. On-demand "Run Now" with 3/day rate limit
10. RRG scatter chart (Recharts)
11. Sector Scorecard view

### Phase 3: Narrative & History
12. Narrative generator agent
13. Analysis History browser
14. Oversold detector

### Rationale
- Phase 1: end-to-end prototype (data → agents → DB → browser)
- Phase 2: differentiating analytics (RRG) + automation
- Phase 3: AI narrative polish + historical comparison

### Dependencies
- ANTHROPIC_API_KEY required for all phases
- FRED_API_KEY required for Phase 1 (graceful degradation)
- SQLite = zero-config
