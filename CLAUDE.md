# SectorPulse implementation status

Read README.md and VERIFICATION.md for capabilities and limitations.
FastAPI, React, SQLite snapshots/runs/jobs, background refresh, separate strength/risk/macro,
a custom relative-strength map, retrospective holdout and optional AI explanation are implemented.
This is a single-instance private research MVP, not a certified point-in-time backtest.
Never pass dates, raw history or arbitrary provider strings to an LLM.
AI must never change deterministic results. Never commit .env, credentials or local databases.
Preserve saved inputs and failure states. Do not tune rules to improve the recorded holdout.
