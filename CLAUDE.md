# SectorPulse

AI-powered sector rotation analytics dashboard. Uses Claude agents to analyze macroeconomic conditions, score market sectors, and generate portfolio allocation recommendations with RRG (Relative Rotation Graph) visualization.

## Architecture

- **Backend**: FastAPI + SQLite (async via aiosqlite/SQLAlchemy), Python 3.11+
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Recharts
- **AI**: LangChain + Claude (claude-sonnet-4-6) for macro analysis, sector scoring, portfolio allocation, and narrative generation

## Dev Commands

### Backend
```bash
cd backend
pip install -e .          # Install dependencies
uvicorn app.main:app --reload --port 8000   # Run dev server
pytest                    # Run tests
ruff check .              # Lint
mypy app/                 # Type check
```

### Frontend
```bash
cd frontend
npm install               # Install dependencies
npm run dev               # Run dev server (port 5173, proxies /api to :8000)
npm run build             # Production build
npm run lint              # Lint
```

## Key Rules
- Never pass dates to agent prompts (anti-look-ahead-bias)
- All agents use claude-sonnet-4-6 (not opus)
- FRED API must degrade gracefully if key is missing
- Single analysis run (no triple-run median)
