---
tags:
  - factory
  - source
  - sectorpulse-spec
source: factory-archivist
date: 2026-08-07
---

# Pitfalls and Mitigations

## Findings

### yfinance Rate Limits
- Yahoo Finance throttles at ~2000 req/hour. Only 12 tickers per run, so low risk.
- Mitigation: 1-2s delays between tickers, cache in SQLite, existing _retry_with_backoff.
- Fallback: yahoo_fin or Polygon.io free tier if yfinance breaks.

### FRED API
- Requires free key. 120 req/min limit (generous for 9 series).
- Mitigation: Degrade gracefully without key — RRG still works with price data only. Show warning banner.

### Claude API Costs
- 3-4 Claude calls per analysis run. ~$0.50-1.50/day at 4 runs/day.
- Mitigation: Use claude-sonnet-4-6 instead of opus (5-10x cheaper). Single-run vs triple-run saves 2/3 cost. Rate-limit manual runs to 3/day.

### Anti-Look-Ahead Bias (Critical)
- Spec mandates no dates in prompts. Existing agent code already compliant.
- Mitigation: Narrative generator (new) must also follow this rule. Add unit test grepping prompts for date patterns.

### yfinance Data Quality
- Stale/incomplete data possible outside market hours.
- Mitigation: Validate data recency (within 3 trading days). Schedule at 4:30 PM ET. Show "data may be delayed" warning.

### SQLite Concurrency
- Limited write concurrency. Max ~4 runs/day = negligible contention.
- Mitigation: WAL mode (PRAGMA journal_mode=WAL).
