"""Tests for RRG quadrant classifier and oversold detector."""

import numpy as np
import pandas as pd
import pytest

from app.data.rrg import _classify_quadrant, compute_rrg, wma
from app.data.oversold import detect_oversold


# ---------------------------------------------------------------------------
# WMA tests
# ---------------------------------------------------------------------------


class TestWMA:
    def test_known_values(self):
        """WMA of constant series should equal that constant."""
        data = pd.Series([5.0] * 20)
        result = wma(data, window=10)
        # First 9 values are NaN (need 10 points), rest should be 5.0
        assert result.iloc[9] == pytest.approx(5.0)
        assert result.iloc[-1] == pytest.approx(5.0)

    def test_ascending_weights(self):
        """WMA with ascending data should weight recent values more."""
        data = pd.Series(range(1, 11), dtype=float)
        result = wma(data, window=10)
        # weights = [1,2,...,10], sum=55
        # dot([1..10], [1..10]) = sum of i^2 = 385
        expected = 385.0 / 55.0
        assert result.iloc[9] == pytest.approx(expected)

    def test_nan_before_window(self):
        """Values before the window is filled should be NaN."""
        data = pd.Series([1.0] * 15)
        result = wma(data, window=10)
        assert all(pd.isna(result.iloc[:9]))
        assert not pd.isna(result.iloc[9])

    def test_window_3(self):
        """Test small window for easier manual verification."""
        # weights = [1, 2, 3], sum = 6
        data = pd.Series([10.0, 20.0, 30.0])
        result = wma(data, window=3)
        expected = (10 * 1 + 20 * 2 + 30 * 3) / 6.0
        assert result.iloc[2] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Quadrant classification tests
# ---------------------------------------------------------------------------


class TestQuadrantClassification:
    def test_leading(self):
        assert _classify_quadrant(105.0, 101.0) == "Leading"

    def test_weakening(self):
        assert _classify_quadrant(105.0, 99.0) == "Weakening"

    def test_lagging(self):
        assert _classify_quadrant(95.0, 99.0) == "Lagging"

    def test_improving(self):
        assert _classify_quadrant(95.0, 101.0) == "Improving"

    def test_all_four_quadrants_reachable(self):
        """Verify all 4 quadrants are achievable."""
        quadrants = {
            _classify_quadrant(110, 110),
            _classify_quadrant(110, 90),
            _classify_quadrant(90, 90),
            _classify_quadrant(90, 110),
        }
        assert quadrants == {"Leading", "Weakening", "Lagging", "Improving"}


# ---------------------------------------------------------------------------
# compute_rrg integration tests
# ---------------------------------------------------------------------------


class TestComputeRRG:
    def _make_prices(self, sector_trend: float, n: int = 60) -> tuple:
        """Create synthetic price data.

        sector_trend > 1.0 means sector outperforms benchmark.
        """
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        benchmark = pd.Series(
            100.0 * np.cumprod(1 + np.full(n, 0.001)), index=dates
        )
        sector = pd.Series(
            100.0 * np.cumprod(1 + np.full(n, 0.001 * sector_trend)),
            index=dates,
        )
        prices_df = pd.DataFrame({"SECT": sector})
        return prices_df, benchmark

    def test_outperforming_sector(self):
        """Sector consistently beating benchmark should be Leading or Weakening."""
        prices_df, benchmark = self._make_prices(sector_trend=2.0, n=60)
        result = compute_rrg(prices_df, benchmark)
        assert "SECT" in result
        assert result["SECT"]["rs_ratio"] > 100

    def test_underperforming_sector(self):
        """Sector consistently trailing benchmark should be Lagging or Improving."""
        prices_df, benchmark = self._make_prices(sector_trend=0.5, n=60)
        result = compute_rrg(prices_df, benchmark)
        assert "SECT" in result
        assert result["SECT"]["rs_ratio"] < 100

    def test_trail_length(self):
        """Trail should contain up to trail_length points."""
        prices_df, benchmark = self._make_prices(sector_trend=1.5, n=60)
        result = compute_rrg(prices_df, benchmark, trail_length=5)
        assert "SECT" in result
        assert len(result["SECT"]["trail"]) == 5

    def test_trail_contains_ratio_and_momentum(self):
        prices_df, benchmark = self._make_prices(sector_trend=1.5, n=60)
        result = compute_rrg(prices_df, benchmark)
        for point in result["SECT"]["trail"]:
            assert "rs_ratio" in point
            assert "rs_momentum" in point

    def test_insufficient_data_skipped(self):
        """Tickers with too few data points should be skipped."""
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        prices_df = pd.DataFrame({"SHORT": [100, 101, 102, 103, 104]}, index=dates)
        benchmark = pd.Series([100, 101, 102, 103, 104], index=dates)
        result = compute_rrg(prices_df, benchmark, window=10)
        assert "SHORT" not in result

    def test_quadrant_field_present(self):
        prices_df, benchmark = self._make_prices(sector_trend=1.5, n=60)
        result = compute_rrg(prices_df, benchmark)
        assert result["SECT"]["quadrant"] in {
            "Leading", "Weakening", "Lagging", "Improving"
        }


# ---------------------------------------------------------------------------
# Oversold detector tests
# ---------------------------------------------------------------------------


class TestDetectOversold:
    def _make_declining_prices(self, tickers: list[str], n: int = 80) -> pd.DataFrame:
        """Create price data with consistent declines."""
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        data = {}
        for ticker in tickers:
            # Declining prices: start at 100, lose 0.3% per day
            data[ticker] = 100.0 * np.cumprod(1 + np.full(n, -0.003))
        return pd.DataFrame(data, index=dates)

    def _make_rising_prices(self, tickers: list[str], n: int = 80) -> pd.DataFrame:
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        data = {}
        for ticker in tickers:
            data[ticker] = 100.0 * np.cumprod(1 + np.full(n, 0.003))
        return pd.DataFrame(data, index=dates)

    def test_oversold_detected(self):
        """A declining sector aligned with cycle phase should be oversold."""
        # XLF is first in recovery favored list
        prices = self._make_declining_prices(["XLF"])
        result = detect_oversold(prices, "recovery")
        xlf = next(r for r in result if r["ticker"] == "XLF")
        assert xlf["is_oversold"] is True
        assert xlf["price_return_1m"] < 0
        assert xlf["price_return_3m"] < 0
        assert xlf["cycle_alignment"] > 60

    def test_not_oversold_when_rising(self):
        """A rising sector should not be oversold even if cycle-aligned."""
        prices = self._make_rising_prices(["XLF"])
        result = detect_oversold(prices, "recovery")
        xlf = next(r for r in result if r["ticker"] == "XLF")
        assert xlf["is_oversold"] is False

    def test_not_oversold_when_not_aligned(self):
        """A declining sector NOT aligned with cycle should not be oversold."""
        # XLK is not in recovery favored list
        prices = self._make_declining_prices(["XLK"])
        result = detect_oversold(prices, "recovery")
        xlk = next(r for r in result if r["ticker"] == "XLK")
        assert xlk["is_oversold"] is False
        assert xlk["cycle_alignment"] == 0.0

    def test_output_fields(self):
        """Check all expected output fields are present."""
        prices = self._make_declining_prices(["XLE"])
        result = detect_oversold(prices, "expansion")
        assert len(result) == 1
        entry = result[0]
        assert set(entry.keys()) == {
            "ticker", "price_return_1m", "price_return_3m",
            "cycle_alignment", "is_oversold",
        }

    def test_unknown_phase(self):
        """Unknown cycle phase should produce zero alignment for all."""
        prices = self._make_declining_prices(["XLF"])
        result = detect_oversold(prices, "unknown_phase")
        xlf = next(r for r in result if r["ticker"] == "XLF")
        assert xlf["cycle_alignment"] == 0.0
        assert xlf["is_oversold"] is False
