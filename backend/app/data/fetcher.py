"""Data fetcher for sector ETF prices and FRED macro indicators.

Fetches latest data only (no historical backtest ranges). FRED degrades
gracefully when FRED_API_KEY is not set — returns empty results with a
logged warning instead of raising.
"""

import logging
import os
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from app.config import (
    BENCHMARK_TICKER,
    FRED_SERIES,
    FRED_SERIES_V2,
    SECTOR_LAUNCH_DATES,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
LOOKBACK_TRADING_DAYS = 60


def _retry_with_backoff(func, *args, **kwargs):
    """Call *func* with exponential backoff on failure (max MAX_RETRIES attempts)."""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning("Attempt %d failed, retrying in %.1fs …", attempt + 1, wait)
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Sector ETF prices
# ---------------------------------------------------------------------------

def _download_ticker(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Download adjusted close for a single ticker via yfinance."""
    data = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=True,
    )
    if data.empty:
        logger.warning("No data returned for %s", ticker)
        return pd.DataFrame()
    close = data[["Close"]].copy()
    close.columns = [ticker]
    return close


def fetch_sector_prices() -> pd.DataFrame:
    """Fetch the last ~60 trading days of sector ETF + SPY prices.

    Returns a DataFrame with dates as index and tickers as columns.
    """
    today = date.today()
    # ~60 trading days ≈ 90 calendar days with buffer
    start = today - timedelta(days=90)

    frames: list[pd.DataFrame] = []

    tickers_with_starts: list[tuple[str, date]] = []
    for ticker, launch in SECTOR_LAUNCH_DATES.items():
        effective_start = max(start, launch)
        if effective_start <= today:
            tickers_with_starts.append((ticker, effective_start))
    tickers_with_starts.append((BENCHMARK_TICKER, start))

    for ticker, t_start in tickers_with_starts:
        logger.info("Fetching %s from %s to %s", ticker, t_start, today)
        df = _retry_with_backoff(_download_ticker, ticker, t_start, today)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError("No price data fetched — check network connectivity")

    prices = pd.concat(frames, axis=1).sort_index()
    logger.info("Fetched prices: %d rows, %d columns", len(prices), len(prices.columns))
    return prices


# ---------------------------------------------------------------------------
# FRED macro indicators
# ---------------------------------------------------------------------------

def _get_fred_client():
    """Return a Fred client, or None if FRED_API_KEY is not set."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        logger.warning(
            "FRED_API_KEY not set — macro indicators will be unavailable. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        return None
    from fredapi import Fred
    return Fred(api_key=api_key)


def fetch_macro_indicators() -> dict[str, pd.Series]:
    """Fetch latest FRED macro indicator series.

    Returns a dict mapping indicator name → Series.
    If FRED_API_KEY is not set, returns an empty dict.
    """
    fred = _get_fred_client()
    if fred is None:
        return {}

    results: dict[str, pd.Series] = {}
    all_series = {**FRED_SERIES, **FRED_SERIES_V2}

    for name, series_id in all_series.items():
        try:
            logger.info("Fetching FRED series %s (%s)", name, series_id)
            series = _retry_with_backoff(fred.get_series, series_id)
            if series is not None and not series.empty:
                results[name] = series
        except Exception:
            logger.warning("Failed to fetch FRED series %s (%s), skipping", name, series_id)

    return results


def get_latest_macro_snapshot() -> dict[str, float]:
    """Return a flat dict of the latest value for each macro indicator.

    This is the format consumed by agent prompts. If FRED_API_KEY is not
    set, returns an empty dict with a logged warning.
    """
    indicators = fetch_macro_indicators()
    snapshot: dict[str, float] = {}
    for name, series in indicators.items():
        latest = series.dropna().iloc[-1] if not series.dropna().empty else None
        if latest is not None:
            snapshot[name] = float(latest)
    return snapshot
