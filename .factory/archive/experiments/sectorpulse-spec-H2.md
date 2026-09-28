---
tags:
  - factory
  - experiment
  - sectorpulse-spec
project: sectorpulse-spec
experiment_id: H2
verdict: KEEP
score_delta: N/A
date: 2026-08-07
source: factory-archivist
---

# Experiment H2: Port config + data fetcher (adapted for latest-only)

## Hypothesis
Port config.py (removing backtest constants) and create a latest-only data fetcher with graceful FRED degradation.

## Result
**KEEP** — CEO verdict: PROCEED, zero issues found.

## What Changed
- `backend/app/config.py` — ported from source with backtest constants removed. Retains SECTOR_TICKERS, BENCHMARK_TICKER, SECTOR_LAUNCH_DATES, FRED_SERIES, FRED_SERIES_V2, CYCLE_SECTOR_MAP, get_available_sectors().
- `backend/app/data/fetcher.py` — adapted fetcher for latest-only data (last 60 trading days for prices, latest FRED values). Removed parquet storage and ALFRED vintage logic. FRED degrades gracefully if API key missing. Includes `get_latest_macro_snapshot()`.
- 12 tests passing confirming FRED graceful degradation.
- Commit: `964e678`

## Links
- Project: sectorpulse-spec
- Commit: 964e678
