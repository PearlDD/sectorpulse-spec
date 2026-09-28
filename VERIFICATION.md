# Verification — v0.3

Verified 2026-09-28 using Python 3.12.3 and Node 25.6.1. Documented installation target: Python 3.12 and Node 24 LTS on macOS/Linux.

## Automated checks

- **43 pytest tests passed**: configuration, launch eligibility, explicit historical cutoff/future filtering, no-FRED behavior, provider retries/empty responses/partial failures, vintage parameters, common-session scoring, independent macro/risk, low-coverage gating, snapshot serialization/hash/replay, concurrent job deduplication/queue cap, failure preservation, restart interruption, exclusive worker lock, real subprocess timeout, rotation formula, chronological signal selection/next-close entry/costs/forward gaps, consistent synthetic history, AI whitelist/schema and separate success/failure persistence, and the asynchronous API lifecycle.
- Compatibility price/macro/analysis reads reject a mismatched requested cutoff rather than returning another date's research.
- Ruff, mypy, strict frontend TypeScript, ESLint and Vite production build passed through `python eval/score.py`.
- `git diff --check`, `bash -n run.sh`, `docker compose config --quiet`: passed.
- One upstream Starlette/httpx TestClient deprecation warning remains; no warnings are hidden. No runtime failure observed from this warning.

## Real data and browser checks

A live run requested on 2026-09-28 with cutoff **2025-12-31** returned **11/11 comparable sectors**. FRED was unconfigured and visibly unavailable; the report was correctly marked partial. Synthetic mode also completed without provider keys. The original sanitized inputs and report persisted in local SQLite. Replay returned `matches_saved: true` and fingerprint `a66c3274e52b863f67481f665ae010aa84a8b3d20ac37b5461dd572bc08d7abe`.

The live holdout evaluated **18 periods**, skipped **0**, and returned mean excess **−0.0555 percentage points** with a 55.6% outperformance frequency. This does not establish an edge. The rule was not tuned to improve that result. [Saved validation evidence](eval/reports/validation-2025-12-31.json) contains dates, parameters and every evaluated period; raw provider prices and the private database are not committed.

Manual browser checks covered the live saved report, missing FRED state, history, separate risk/macro, custom map, per-period validation, and successful reproducibility verification. An explicit AI request returned content that failed schema validation safely and left the deterministic report unchanged; after page reload its failed state remained visible. The request now uses Anthropic structured outputs after that failure; a real retry awaits explicit transmission/billing approval. Successful end-to-end AI output is **not** claimed. Automated mocked tests verify successful parsing/persistence and failure isolation.

At a 390×844 viewport, document client width and scroll width were both 375px (browser scrollbar accounts for the difference): no page-level horizontal overflow. Responsive tables remain horizontally scrollable within their panels. Browser testing was manual, not an automated end-to-end suite.

## Unverified / operational limits

- FRED real-key success not exercised. Vintage parameters and missing-key/provider-failure paths are mocked in tests.
- Docker daemon was unavailable, so configuration syntax passed but image build/container startup were not verified.
- No external deployment, account creation or production traffic test occurred.
- Single local SQLite instance/dispatcher only; no multi-replica or failover support.
- No certified historical point-in-time feed, full exchange calendar, calibrated trading costs or prospective untouched validation.

## Main changed files

- `backend/app/db/store.py`: durable queue, snapshots, runs and separate explanations.
- `backend/app/services/jobs.py`: worker isolation, deadlines, recovery and safe failures.
- `backend/app/data/snapshot.py`, `demo.py`, `fetcher.py`: saved inputs, consistent demo history and longer historical acquisition.
- `backend/app/analysis.py`, `validation.py`: independent strength/risk/macro, map and temporal validation.
- `backend/app/services/explanation.py`: explicit date-free numeric whitelist and validated optional prose.
- `backend/app/main.py`: queued refresh API, journal/replay routes and cached compatibility reads.
- `backend/tests/test_reliability.py`, `test_mvp.py`: reliability and research contract tests.
- `frontend/src/App.tsx`, `api.ts`, `ResearchCharts.tsx`, `index.css`: working journal/dashboard, durable task state, independent evidence and charts.
- Docker/Compose/environment exclusions: persistent non-root storage and optional server-only AI key.
- README (English/Chinese), CLAUDE and this record: setup, methodology, deployment and accurate limitations.
