# v0.4 research desk

New current-only research lives in app/data/research.py and app/services/research.py. It is independent of historical price snapshots. Never feed arbitrary news into LLM instructions; no automated AI calls. Never fabricate consensus, publication timestamps, full-text verification or valuation/bottom signals. Public FRED CSV is revised current-vintage data, not a historical backtest. Calendar times are America/New_York; BLS uses the nonstandard US-Eastern alias. Persist old sources on failure, exclude stale evidence and preserve archives. Run eval/score.py with SECTORPULSE_RESEARCH_AUTO=0 for isolated tests.

# SectorPulse implementation status

Read README.md and VERIFICATION.md for capabilities and limitations.
FastAPI, React, SQLite snapshots/runs/jobs, background refresh, separate strength/risk/macro,
a custom relative-strength map, retrospective holdout and optional AI explanation are implemented.
This is a single-instance private research MVP, not a certified point-in-time backtest.
Never pass dates, raw history or arbitrary provider strings to an LLM.
AI must never change deterministic results. Never commit .env, credentials or local databases.
Preserve saved inputs and failure states. Do not tune rules to improve the recorded holdout.
