# v0.5 verification — 2026-10-15

- Full evaluation passed: backend tests, Ruff, mypy, frontend types, lint and production build. Added sector tests cover all 11 main sectors plus 4 distinct subindustries, all price-state branches, exact heat thresholds, stale/demo/future/missing reports, nonfinite values and no inheritance of parent prices.
- The language-rendering test passed: Chinese/English labels, preserved whitespace, date-range wording, accessible labels and unchanged canonical select values. It is now included in eval/score.py.
- Browser checks confirmed all 11 main-sector cards, state counts from the actual saved live report, heat filtering, subindustry filtering, state retention during language changes, and English preference persistence after reload. In English mode, the only visible Chinese text was the intentional 中文 language-switch label.
- Verified the current narrow browser (304px) and the wide reference layout (1425px content width); neither had document-level horizontal overflow. Reset the temporary wide viewport after checking. Source headlines remain original text.
- Price groups are descriptive rules based on a recent immutable live price report, not an overvaluation/crowding measure or a fundamental-cycle conclusion. Subindustries without direct price reports remain explicitly unclassified. Fundamental confirmation and valuation gaps remain visible.

---

# v0.4 verification — 2026-10-15

- Existing full evaluation passed (backend tests, Ruff, mypy, strict frontend types, lint, production build). The final source-classification fixes passed all 15 focused research tests plus Ruff and mypy.
- Real local acquisition succeeded for all 20 resources: 13 FRED series, 4 RSS feeds, BLS/BEA ICS and FOMC HTML. Empty topic-matching news results are distinguished from acquisition failures.
- Browser verified the macro desk, manual refresh progress, official event dates with US daylight saving transitions, important-event filtering, news topic filtering and source status. Default viewport content width matched client width (1265px).
- Fixed real-source issues: BLS US-Eastern timezone alias, missing-month FRED comparison by actual calendar endpoints, regional personal-income/GDP classification, and substring false positives in news matching.
- Automated coverage includes missing/stale inputs, invalid/future observations, ICS folded lines/UTC/all-day/DST, FOMC parsing, election dates, no fabricated consensus, failure preservation, archived source inputs, duplicate news, scheduler slots and read-only API behavior.
- Local background service and double-click startup entry prepared; shell syntax checked. Reboot/login autostart is not configured. No cloud or Supabase changes and no automatic paid AI calls.
- Limitations: title-only news and conditional transmission templates, no full-text synthesis, no consensus surprises, no verified industry valuation/orders/inventory feed or buy ranking, no prospective evidence of predictive returns. Scheduling cannot collect while the computer sleeps or the service is stopped.

---

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
