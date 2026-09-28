"""Canonical sanitized inputs, independent of providers and future revisions."""

from datetime import date

import numpy as np
import pandas as pd

from app.config import FRED_SERIES, FRED_SERIES_V2
from app.db.store import now

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
MAX_AGE = {
    "MANUFACTURING_EMPLOYMENT": 75,
    "YIELD_CURVE": 10,
    "INITIAL_CLAIMS": 21,
    "OECD_CLI": 120,
    "UNEMPLOYMENT": 75,
    "CPI": 75,
    "HY_SPREAD": 10,
    "IG_SPREAD": 10,
    "VIX": 10,
}


def clean(series: pd.Series, end: date) -> pd.Series:
    series = series.copy()
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    series = (
        pd.to_numeric(series, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    series = series.loc[~series.index.duplicated(keep="last")].sort_index()
    return series.loc[series.index <= pd.Timestamp(end)]


def points(series: pd.Series) -> list[dict]:
    return [
        {"date": pd.Timestamp(str(day)).date().isoformat(), "value": float(value)}
        for day, value in series.items()
    ]


def make_snapshot(
    prices: pd.DataFrame,
    macro: dict[str, pd.Series],
    end: date,
    mode: str,
    fred_configured: bool,
) -> dict:
    return {
        "schema_version": 1,
        "as_of_date": end.isoformat(),
        "fetched_at": now(),
        "mode": mode,
        "sources": {
            "prices": "synthetic" if mode == "demo" else "Yahoo adjusted close",
            "macro": "synthetic" if mode == "demo" else "FRED/ALFRED vintage",
            "macro_vintage": end.isoformat(),
            "fred_configured": fred_configured,
        },
        "prices": {
            ticker: points(clean(prices[ticker], end).where(lambda x: x > 0).dropna())
            for ticker in prices
        },
        "macro": {name: points(clean(series, end)) for name, series in macro.items()},
        "unavailable": dict(prices.attrs.get("unavailable", {})),
        "price_basis": "provider-adjusted close; historical revisions possible",
        "calendar_policy": "SPY observed sessions; no forward fill; seven-calendar-day freshness bound",
    }


def restore(snapshot: dict) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    def series(rows):
        return pd.Series(
            [p["value"] for p in rows],
            index=pd.to_datetime([p["date"] for p in rows]),
            dtype=float,
        )

    prices = pd.DataFrame(
        {ticker: series(rows) for ticker, rows in snapshot["prices"].items()}
    ).sort_index()
    prices.attrs["unavailable"] = snapshot["unavailable"]
    return prices, {name: series(rows) for name, rows in snapshot["macro"].items()}


def macro_payload(snapshot: dict) -> dict:
    end = pd.Timestamp(snapshot["as_of_date"])
    rows = []
    for name, series_id in {**FRED_SERIES, **FRED_SERIES_V2}.items():
        values = snapshot["macro"].get(name, [])
        latest = values[-1] if values else None
        age = (end - pd.Timestamp(latest["date"])).days if latest else None
        rows.append(
            {
                "name": name,
                "series_id": series_id,
                "unit": UNITS[name],
                "value": latest["value"] if latest else None,
                "observation_date": latest["date"] if latest else None,
                "age_days": age,
                "status": "unavailable"
                if latest is None
                else "stale"
                if age is not None and age > MAX_AGE[name]
                else "available",
            }
        )
    available = sum(row["status"] == "available" for row in rows)
    return {
        "status": "available"
        if available == len(rows)
        else "partial"
        if available
        else "unavailable",
        "reason": "Synthetic demo inputs"
        if snapshot["mode"] == "demo"
        else "FRED_API_KEY is missing"
        if not snapshot["sources"]["fred_configured"]
        else "Historical vintage; freshness shown per indicator",
        "indicators": rows,
    }
