---
tags:
  - factory
  - source
  - sectorpulse-spec
source: factory-archivist
date: 2026-08-07
---

# RRG (Relative Rotation Graph) Algorithm

## Findings

RRG is pure math — no LLM needed. Based on Julius de Kempenaer methodology.

### Algorithm
1. **Relative Strength**: RS = (sector_price / benchmark_price) * 100 (SPY as benchmark)
2. **JdK RS-Ratio**: Double-smoothed WMA(10) of RS, normalized around 100
3. **JdK RS-Momentum**: Rate of change of RS-Ratio, normalized around 100
4. **Quadrant Classification**:
   - Leading: RS-Ratio > 100, RS-Momentum > 100
   - Weakening: RS-Ratio > 100, RS-Momentum < 100
   - Lagging: RS-Ratio < 100, RS-Momentum < 100
   - Improving: RS-Ratio < 100, RS-Momentum > 100 (Next-Hot candidates)

### Key Insight
The "Improving" quadrant maps directly to the Next-Hot Predictor feature. Sectors moving Lagging → Improving are turnaround candidates.

### Reference Implementations
- [RRGPy](https://github.com/An0n1mity/RRGPy)
- [RRG Sector Rotation India](https://github.com/AdroitAnandAI/RRG-Sector-Rotation-India)
- [StockCharts RRG ChartSchool](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts)
- [RRG Algorithm Gist](https://gist.github.com/tuhuynh27/c8abcf7f8469b7d91adac9a6947db64d)
