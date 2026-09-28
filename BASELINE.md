# Archive inspection baseline

The original archive had 44 entries and no populated agents or database implementation. Its source/config/test files, frontend configuration and dependencies, evaluation harness, and documentation were inspected.

Implemented: the 11 SPDR ticker list plus SPY, sector launch dates, a four-phase sector mapping, basic yfinance and optional FRED fetching, a health endpoint, and 12 passing configuration/missing-key tests. The original tests were subsequently run successfully together with the new tests.

Placeholder/missing: the React page only displayed “SectorPulse”; agent/db/api packages were empty; there was no scoring, analysis API, RRG, persistence, deployment configuration, or LLM implementation. CLAUDE.md described intended capabilities rather than implemented ones.

Gaps: price fetching always used today; ticker exceptions aborted the full request; empty downloads were not retried; macro data was unconstrained and used revised latest values; MANEMP was mislabeled PMI; the evaluator could accept absent tools; mypy/Ruff were not in test dependencies; frontend dependencies included unused routing and starter assets.

Smallest end-to-end path: bounded and independently resilient data fetching, conservative macro vintage handling, transparent relative-performance scoring plus the existing cycle map, useful JSON endpoints, and an interactive React dashboard. Preserve FastAPI and the existing frontend stack. Defer LLM, RRG, persistence, and allocations rather than overclaiming them.
