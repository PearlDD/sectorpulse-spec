# Verification

Verified on 2026-09-24 with Python 3.12.3 and Node 25.6.1. The documented target is Python 3.12 and Node 24 LTS.

- `pytest`: **29 passed**. Covers original config/launch-date/no-key behavior plus explicit cutoffs, future-row filtering, retry backoff/exhaustion, empty results, partial ticker failures, FRED vintage query parameters, missing values, secret-safe logs, score formula/order/ties, missing sessions, stale inputs, cycle phases/bonuses, API demo, API validation/failure, and price-only live-mode analysis.
- `ruff check .`: passed.
- `mypy app/`: passed for all 10 application source files.
- `npm run typecheck`: passed with strict TypeScript enabled.
- `npm run lint`: passed.
- `npm run build`: passed; split output chunks are approximately 192 KB and 376 KB before compression, with no chunk-size warning.
- `python eval/score.py`: all six checks passed.
- `bash -n run.sh` and `docker compose config --quiet`: passed.
- FastAPI production static serving: `/` returned the compiled React app; demo analysis returned 11 ranked sectors and 12 price series over HTTP.
- Browser verification: live data refresh, missing FRED state, partial price coverage, demo refresh, timestamp updates, sector selection/rationale/chart changes, and desktop layout. Production mobile check at a 390px viewport reported document client width and scroll width both 375px (15px browser scrollbar), confirming no page-level horizontal overflow. The ranking table scrolls within its panel.

Live Yahoo checks returned data but only two sectors met the strict common-session requirement at the tested cutoff; the other nine were visibly excluded. Provider completeness is not guaranteed. Synthetic mode showed all 11 sectors. FRED live-success behavior was not checked because no key was supplied; HTTP-mocked tests verify vintage parameters and failure behavior.

The installed Starlette test client emits one upstream deprecation warning about its httpx adapter. Tests pass; runtime API behavior is unaffected. No warnings are suppressed.

Docker configuration syntax passed, but a container build/run was not tested because the Docker daemon was not running. No external deployment occurred. Browser inspection was manual; no automated frontend interaction test suite is claimed.

## Changed files

- `backend/app/config.py`: corrected macro labels and added sector display names.
- `backend/app/data/fetcher.py`: historical cutoff, provider validation/retries, partial isolation, FRED vintage support, safe diagnostics.
- `backend/app/data/demo.py` (new): explicitly synthetic, deterministic fixtures.
- `backend/app/analysis.py` (new): common-window relative returns, cycle heuristic, score components, exclusions.
- `backend/app/main.py`: health/prices/macro/analysis API, useful errors, timestamps, production frontend serving.
- `backend/tests/test_mvp.py` (new), existing test formatting: 29 total tests.
- `backend/pyproject.toml`, `backend/requirements.lock` (new): usable runtime/test dependencies, lint/type settings, pinned environment.
- `frontend/src/App.tsx`, `index.css`, `main.tsx`: interactive responsive dashboard and lazy-loaded bundle.
- `frontend/tsconfig.app.json`, `package.json`, `index.html`: strict typing, check command, product metadata.
- `eval/score.py`: frontend verification and failure on missing check tools.
- `.env.example`, `.gitignore`: optional server-only key and secret/cache exclusions.
- `run.sh`, `Dockerfile`, `compose.yaml`, `.dockerignore` (new): local setup and undeployed hosting configuration.
- `README.md`, `BASELINE.md`, `VERIFICATION.md` (new), `CLAUDE.md`: accurate capabilities, methodology, setup, deployment, and remaining gaps.
