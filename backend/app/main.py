import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.analysis import score_sectors
from app.config import FRED_SERIES, FRED_SERIES_V2
from app.data.demo import demo_macro, demo_prices
from app.data.fetcher import fetch_macro_indicators, fetch_sector_prices, resolve_date

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
# HTTP clients can log URLs containing provider credentials.
logging.getLogger("httpx").setLevel(logging.WARNING)
app = FastAPI(title="SectorPulse", version="0.2.0")
Mode = Literal["live", "demo"]


def cutoff(value: date | None) -> date:
    try:
        return resolve_date(value)
    except ValueError as exc:
        raise HTTPException(
            422, detail={"code": "invalid_date", "message": str(exc)}
        ) from None


def prices_for(end: date, mode: Mode):
    try:
        return demo_prices(end) if mode == "demo" else fetch_sector_prices(end)
    except RuntimeError:
        raise HTTPException(
            503,
            detail={
                "code": "prices_unavailable",
                "message": "Price provider unavailable. Retry later or select synthetic demo.",
            },
        ) from None


def macro_for(end: date, mode: Mode):
    return demo_macro(end) if mode == "demo" else fetch_macro_indicators(end)


UNITS = {
    "MANUFACTURING_EMPLOYMENT": "thousand persons",
    "YIELD_CURVE": "percentage points",
    "INITIAL_CLAIMS": "persons",
    "OECD_CLI": "index",
    "UNEMPLOYMENT": "%",
    "CPI": "index (1982–84=100)",
    "HY_SPREAD": "%",
    "IG_SPREAD": "%",
    "VIX": "index",
}


def macro_payload(data, end: date, mode: Mode) -> dict:
    entries = []
    for name, series_id in {**FRED_SERIES, **FRED_SERIES_V2}.items():
        series = data.get(name)
        available = series is not None and not series.empty
        entries.append(
            {
                "name": name,
                "series_id": series_id,
                "unit": UNITS[name],
                "value": float(series.iloc[-1]) if available else None,
                "observation_date": series.index[-1].date().isoformat()
                if available
                else None,
                "age_days": (pd_timestamp(end) - series.index[-1]).days
                if available
                else None,
                "status": "available" if available else "unavailable",
            }
        )
    return {
        "as_of_date": end.isoformat(),
        "source": "synthetic" if mode == "demo" else "FRED/ALFRED",
        "status": "available"
        if len(data) == len(entries)
        else "partial"
        if data
        else "unavailable",
        "reason": "Synthetic demo inputs"
        if mode == "demo"
        else "FRED_API_KEY is missing"
        if not os.getenv("FRED_API_KEY", "").strip()
        else "Vintage-limited observations; individual series may be unavailable",
        "indicators": entries,
    }


def pd_timestamp(value):
    import pandas as pd

    return pd.Timestamp(value)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "0.2.0",
        "fred_configured": bool(os.getenv("FRED_API_KEY", "").strip()),
        "ai_enabled": False,
    }


@app.get("/api/prices")
def prices(as_of_date: date | None = None, mode: Mode = "live") -> dict:
    end = cutoff(as_of_date)
    frame = prices_for(end, mode)
    return {
        "as_of_date": end.isoformat(),
        "source": "synthetic" if mode == "demo" else "Yahoo Finance (adjusted close)",
        "unavailable": frame.attrs.get("unavailable", {}),
        "series": {
            ticker: [
                {"date": day.date().isoformat(), "close": float(value)}
                for day, value in frame[ticker].dropna().items()
            ]
            for ticker in frame.columns
        },
    }


@app.get("/api/macro")
def macro(as_of_date: date | None = None, mode: Mode = "live") -> dict:
    end = cutoff(as_of_date)
    return macro_payload(macro_for(end, mode), end, mode)


@app.get("/api/analysis")
def analysis(as_of_date: date | None = None, mode: Mode = "live") -> dict:
    end = cutoff(as_of_date)
    frame = prices_for(end, mode)
    indicators = macro_for(end, mode)
    try:
        result = score_sectors(frame, indicators, end)
    except ValueError as exc:
        raise HTTPException(
            503, detail={"code": "insufficient_benchmark", "message": str(exc)}
        ) from None
    return {
        **result,
        "as_of_date": end.isoformat(),
        "mode": mode,
        "status": "partial" if result["excluded"] else "available",
        "updated_at": datetime.now(UTC).isoformat(),
        "prices": {
            ticker: [
                {"date": day.date().isoformat(), "close": float(value)}
                for day, value in frame[ticker].dropna().items()
            ]
            for ticker in frame.columns
        },
        "source": "Synthetic demonstration data"
        if mode == "demo"
        else "Yahoo Finance adjusted prices; FRED vintage macro",
        "macro": macro_payload(indicators, end, mode),
        "ai": {
            "status": "disabled",
            "reason": "No LLM is called. Rankings are deterministic.",
        },
        "limitations": [
            "Educational analytics, not financial advice or a prediction.",
            "Yahoo adjusted history may be revised; this is not a certified point-in-time backtest.",
            "No RRG, database persistence, or AI narrative is implemented.",
        ],
    }


# Serve the compiled React app on the same origin as the API in production.
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="dashboard")
