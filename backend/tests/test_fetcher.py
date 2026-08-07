"""Tests for config constants and data fetcher graceful degradation."""

from datetime import date
from unittest.mock import patch

from app.config import (
    BENCHMARK_TICKER,
    CYCLE_SECTOR_MAP,
    FRED_SERIES,
    FRED_SERIES_V2,
    SECTOR_LAUNCH_DATES,
    SECTOR_TICKERS,
    get_available_sectors,
)
from app.data.fetcher import (
    _get_fred_client,
    fetch_macro_indicators,
    get_latest_macro_snapshot,
)


# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------


class TestConfig:
    def test_sector_tickers_count(self):
        assert len(SECTOR_TICKERS) == 11

    def test_benchmark_ticker(self):
        assert BENCHMARK_TICKER == "SPY"

    def test_all_sector_tickers_have_launch_dates(self):
        for ticker in SECTOR_TICKERS:
            assert ticker in SECTOR_LAUNCH_DATES, f"{ticker} missing launch date"

    def test_fred_series_not_empty(self):
        assert len(FRED_SERIES) > 0
        assert len(FRED_SERIES_V2) > 0

    def test_cycle_sector_map_has_all_phases(self):
        expected_phases = {"recovery", "expansion", "slowdown", "contraction"}
        assert set(CYCLE_SECTOR_MAP.keys()) == expected_phases

    def test_cycle_sector_map_tickers_are_valid(self):
        for phase, tickers in CYCLE_SECTOR_MAP.items():
            for ticker in tickers:
                assert ticker in SECTOR_TICKERS, (
                    f"{ticker} in {phase} not in SECTOR_TICKERS"
                )

    def test_get_available_sectors_all(self):
        result = get_available_sectors(date(2025, 1, 1))
        assert len(result) == 11
        assert result == sorted(result)

    def test_get_available_sectors_before_xlre(self):
        result = get_available_sectors(date(2015, 1, 1))
        assert "XLRE" not in result
        assert "XLC" not in result
        assert len(result) == 9

    def test_get_available_sectors_before_xlc(self):
        result = get_available_sectors(date(2016, 1, 1))
        assert "XLRE" in result
        assert "XLC" not in result
        assert len(result) == 10


# ---------------------------------------------------------------------------
# Fetcher — FRED graceful degradation
# ---------------------------------------------------------------------------


class TestFredGracefulDegradation:
    def test_get_fred_client_returns_none_when_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = _get_fred_client()
            assert client is None

    def test_fetch_macro_indicators_empty_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = fetch_macro_indicators()
            assert result == {}

    def test_get_latest_macro_snapshot_empty_without_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = get_latest_macro_snapshot()
            assert result == {}
