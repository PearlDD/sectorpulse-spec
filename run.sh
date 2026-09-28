#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
.venv/bin/python -m pip install --no-deps -e ./backend
(cd frontend && npm ci && npm run build)
printf '\nSectorPulse is ready at http://127.0.0.1:8000\n'
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
