# SectorPulse

AI-powered US stock market sector rotation analytics. Analyzes the 11 GICS sector ETFs using macro indicators and Claude AI to identify hot sectors, predict rotation, and detect oversold opportunities.

## Features

- **Dashboard** — sector heatmap with AI-generated market narrative
- **RRG Chart** — Relative Rotation Graph showing sector momentum vs relative strength
- **Sector Scorecard** — all 11 sectors at a glance with multi-timeframe returns
- **Oversold Detector** — finds sectors with weak price action but strong fundamentals
- **Scheduled Analysis** — auto-runs daily at 4:30 PM ET
- **Analysis History** — browse and compare past reports

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/PearlDD/sectorpulse-spec.git
cd sectorpulse-spec

# Backend
cd backend
pip install -e ".[test]"

# Frontend
cd ../frontend
npm install
```

### 2. Configure API keys

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...    # Required — for AI narrative generation
FRED_API_KEY=your_fred_key       # Optional — for macro indicators (free at https://fred.stlouisfed.org/docs/api/api_key.html)
```

### 3. Run (development)

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open http://localhost:5173

### 4. Run (production — single process)

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Serve everything from FastAPI
cd backend
uvicorn app.main:app --port 8000
```

Open http://localhost:8000

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, SQLite, APScheduler |
| Frontend | React, TypeScript, Vite, Tailwind, Recharts |
| AI | Claude API (via langchain-anthropic) |
| Data | yfinance (sector ETFs), FRED API (macro indicators) |

## Sector ETFs Tracked

| Ticker | Sector |
|--------|--------|
| XLB | Materials |
| XLC | Communication Services |
| XLE | Energy |
| XLF | Financials |
| XLI | Industrials |
| XLK | Technology |
| XLP | Consumer Staples |
| XLRE | Real Estate |
| XLU | Utilities |
| XLV | Health Care |
| XLY | Consumer Discretionary |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/analysis/run` | Trigger on-demand analysis (3/day limit) |
| GET | `/api/analysis/latest` | Get most recent analysis report |
| GET | `/api/analysis/history` | List past analysis reports |
| GET | `/api/analysis/{id}` | Get specific report by ID |
| GET | `/api/sectors` | Current sector data and scores |
| GET | `/api/rrg` | RRG chart data |
| GET | `/api/macro` | Latest macro indicators |

## Tests

```bash
cd backend
pytest tests/ -v
```

## Design Decisions

- **No dates in AI prompts** — prevents look-ahead bias from LLM's historical knowledge. The agent sees only numerical indicator values, never the date.
- **Numbers computed in code, narratives by AI** — all quantitative signals (momentum, RSI, relative strength, macro regime) are calculated deterministically. Claude only generates human-readable explanations from pre-computed data.
- **Single user, no auth** — designed as a personal analysis tool.
