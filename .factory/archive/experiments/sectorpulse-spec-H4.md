---
tags:
  - factory
  - experiment
  - sectorpulse-spec
project: sectorpulse-spec
experiment_id: H4
verdict: KEEP
score_delta: N/A
date: 2026-08-07
source: factory-archivist
---

# Experiment H4: RRG quadrant math + oversold detector

## Hypothesis
Implement JdK RS-Ratio and RS-Momentum using double-smoothed WMA for RRG quadrant classification. Build oversold detector comparing price momentum against fundamental cycle alignment scores. Both pure math, no LLM calls.

## Result
**KEEP** — CEO verdict: PROCEED, zero issues found.

## What Changed
- Created `backend/app/data/rrg.py`: JdK RS-Ratio and RS-Momentum with double-smoothed WMA (window=10)
  - Input: sector prices DataFrame + SPY benchmark
  - Output: per-sector dict with rs_ratio, rs_momentum, quadrant (Leading/Weakening/Lagging/Improving), trail (last 5 points)
- Created `backend/app/data/oversold.py`: price momentum vs fundamental divergence detector
  - Flags sectors with negative 1m/3m returns but high cycle alignment scores (>60)
  - Output: list with ticker, price_momentum, fundamental_score, divergence_signal
- 20 tests passing (RRG math + oversold detector)
- Commit: `c5e150c`

## Links
- Project: sectorpulse-spec
- Commit: c5e150c
- Phase: 3 (parallel with H3)
