"""Bounded provider requests. Missing observations are never forward-filled."""

import logging
import os
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TypeVar
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pandas as pd
import yfinance as yf

from app.config import (
    FRED_SERIES,
    FRED_SERIES_V2,
    SECTOR_LAUNCH_DATES,
    get_available_sectors,
)

logger = logging.getLogger(__name__)
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.5
T = TypeVar("T")


def resolve_date(as_of_date: date | None = None) -> date:
    today = datetime.now(ZoneInfo("America/New_York")).date()
    end = as_of_date or (today - timedelta(days=1))
    if end >= today or end < date(1999, 1, 1):
        raise ValueError(
            "as_of_date must be between 1999-01-01 and yesterday (completed sessions only)"
        )
    return end


def _retry_with_backoff(func: Callable[..., T], *args, **kwargs) -> T:
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            logger.warning("Provider attempt %d failed; retrying", attempt + 1)
            time.sleep(INITIAL_BACKOFF_SECONDS * 2**attempt)
    raise RuntimeError("Retry exhausted")


def _download_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    raw = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        auto_adjust=True,
        progress=False,
        threads=False,
        timeout=10,
    )
    if raw is None or raw.empty:
        raise ValueError("Empty price response")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close[ticker] if ticker in close.columns else close.iloc[:, 0]
    frame = close.rename(ticker).to_frame()
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    frame = frame.loc[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.loc[(frame.index.date >= start) & (frame.index.date <= end)]
    frame = frame.apply(pd.to_numeric, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    frame = frame.where(frame > 0).dropna()
    if frame.empty:
        raise ValueError("No valid prices within requested range")
    return frame


def fetch_sector_prices(as_of_date: date | None = None) -> pd.DataFrame:
    end = resolve_date(as_of_date)
    start = end - timedelta(days=150)
    frames = []
    unavailable = {}
    for ticker in [*get_available_sectors(end), "SPY"]:
        try:
            frame = _retry_with_backoff(
                _download_ticker,
                ticker,
                max(start, SECTOR_LAUNCH_DATES.get(ticker, start)),
                end,
            )
            frames.append(frame)
        except Exception:  # noqa: BLE001 - isolate provider failures without logging credentials
            logger.warning("Price data unavailable for %s after retries", ticker)
            unavailable[ticker] = "Provider returned no usable data after retries"
    if not frames:
        raise RuntimeError(
            "All price providers failed. Retry later or select demo mode."
        )
    result = pd.concat(frames, axis=1).sort_index()
    result.attrs["unavailable"] = unavailable
    return result


def _get_fred_client():
    # Compatibility helper; never includes key material in logs.
    return os.environ.get("FRED_API_KEY", "").strip() or None


def _fred_series(series_id: str, key: str, end: date) -> pd.Series:
    with httpx.Client(timeout=12) as client:
        response = client.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "api_key": key,
                "file_type": "json",
                "series_id": series_id,
                "observation_start": (end - timedelta(days=550)).isoformat(),
                "observation_end": end.isoformat(),
                "realtime_start": end.isoformat(),
                "realtime_end": end.isoformat(),
            },
        )
        response.raise_for_status()
        rows = response.json().get("observations", [])
    series = pd.Series(
        [x["value"] for x in rows],
        index=pd.to_datetime([x["date"] for x in rows]),
        dtype=object,
    )
    series = (
        pd.to_numeric(series, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .sort_index()
    )
    series = series.loc[series.index <= pd.Timestamp(end)]
    if series.empty:
        raise ValueError("No usable macro observations")
    return series


def fetch_macro_indicators(as_of_date: date | None = None) -> dict[str, pd.Series]:
    end = resolve_date(as_of_date)
    key = _get_fred_client()
    if not key:
        logger.info("FRED_API_KEY absent; macro indicators unavailable")
        return {}
    results = {}
    for name, series_id in {**FRED_SERIES, **FRED_SERIES_V2}.items():
        try:
            results[name] = _retry_with_backoff(_fred_series, series_id, key, end)
        except Exception:  # noqa: BLE001 - isolate provider failures without logging credentials
            logger.warning("FRED series %s unavailable after retries", series_id)
    return results


def get_latest_macro_snapshot(as_of_date: date | None = None) -> dict[str, float]:
    return {
        name: float(series.iloc[-1])
        for name, series in fetch_macro_indicators(as_of_date).items()
    }
