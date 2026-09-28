from datetime import UTC, date, datetime
from unittest.mock import Mock, patch

import httpx
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analysis import cycle_context, score_sectors
from app.data import fetcher
from app.data.demo import demo_macro, demo_prices
from app.main import app

END = date(2025, 1, 31)


def test_explicit_date_partial_failure():
    def download(ticker, start, end):
        assert end == END and start <= end
        if ticker == "XLE":
            raise ConnectionError("private details")
        return pd.DataFrame({ticker: [100.0]}, index=pd.to_datetime(["2025-01-31"]))

    with (
        patch.object(fetcher, "_download_ticker", side_effect=download),
        patch.object(fetcher.time, "sleep"),
    ):
        result = fetcher.fetch_sector_prices(END)
    assert "SPY" in result and "XLE" not in result
    assert "XLE" in result.attrs["unavailable"]


def test_retry():
    call = Mock(side_effect=[TimeoutError(), TimeoutError(), 42])
    with patch.object(fetcher.time, "sleep") as sleep:
        assert fetcher._retry_with_backoff(call) == 42
        assert [c.args[0] for c in sleep.call_args_list] == [0.5, 1.0]
    with patch.object(fetcher.time, "sleep"), pytest.raises(TimeoutError):
        fetcher._retry_with_backoff(Mock(side_effect=TimeoutError))


def test_empty_prices_retry_all_fail():
    with (
        patch.object(fetcher.yf, "download", return_value=pd.DataFrame()) as download,
        patch.object(fetcher.time, "sleep"),
    ):
        with pytest.raises(RuntimeError):
            fetcher.fetch_sector_prices(END)
        assert download.call_count == 36


def test_clip_future_and_invalid_prices():
    frame = pd.DataFrame(
        {("Close", "XLK"): [100, np.inf, 102, 200]},
        index=pd.to_datetime(["2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01"]),
    )
    with patch.object(fetcher.yf, "download", return_value=frame) as download:
        result = fetcher._download_ticker("XLK", date(2025, 1, 29), END)
    assert len(result) == 2 and result.iloc[-1, 0] == 102
    assert download.call_args.kwargs["end"] == "2025-02-01"


def test_fred_vintage_and_missing_values():
    def handler(request):
        for key in ("realtime_start", "realtime_end", "observation_end"):
            assert request.url.params[key] == str(END)
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"date": "2025-01-01", "value": "4"},
                    {"date": "2025-01-20", "value": "."},
                    {"date": "2025-02-01", "value": "99"},
                ]
            },
        )

    with patch.object(
        fetcher.httpx,
        "Client",
        return_value=httpx.Client(transport=httpx.MockTransport(handler)),
    ):
        assert list(fetcher._fred_series("UNRATE", "secret", END)) == [4.0]


def test_macro_failure_redacts_secrets(caplog):
    with (
        patch.dict("os.environ", {"FRED_API_KEY": "private-key"}),
        patch.object(fetcher.time, "sleep"),
        patch.object(fetcher, "_fred_series", side_effect=RuntimeError("private-key")),
    ):
        assert fetcher.fetch_macro_indicators(END) == {}
    assert "private-key" not in caplog.text


def test_scoring_formula_no_future():
    prices = demo_prices(END)
    result = score_sectors(prices, {}, END)
    for row in result["ranking"]:
        assert row["score"] == pytest.approx(
            0.4 * row["relative_20d"] + 0.6 * row["relative_60d"], abs=0.0001
        )
        assert row["cycle_bonus"] == 0
    future = pd.DataFrame(
        {t: [99999] for t in prices.columns}, index=pd.to_datetime(["2025-02-03"])
    )
    assert score_sectors(pd.concat([prices, future]), {}, END) == result
    assert [r["score"] for r in result["ranking"]] == sorted(
        [r["score"] for r in result["ranking"]], reverse=True
    )


def test_missing_sessions_and_benchmark():
    prices = demo_prices(END)
    prices.loc[prices.index[-20], "XLK"] = np.nan
    assert "XLK" in score_sectors(prices, {}, END)["excluded"]
    with pytest.raises(ValueError, match="SPY"):
        score_sectors(prices.drop(columns="SPY"), {}, END)
    with pytest.raises(ValueError, match="stale"):
        score_sectors(prices, {}, date(2025, 2, 15))


def test_weekend_and_ties():
    prices = demo_prices(END)
    prices[:] = 100.0
    result = score_sectors(prices, {}, date(2025, 2, 2))
    assert result["price_date"] == "2025-01-31"
    assert [r["ticker"] for r in result["ranking"]] == sorted(
        r["ticker"] for r in result["ranking"]
    )


@pytest.mark.parametrize(
    "values,spread,phase",
    [
        ([4, 4, 4, 4.4], 1, "contraction"),
        ([4, 4, 4, 4], -1, "slowdown"),
        ([4.4, 4.3, 4.2, 4], 1, "recovery"),
        ([4, 4, 4, 4], 1, "expansion"),
    ],
)
def test_cycle(values, spread, phase):
    dates = pd.date_range(end=pd.Timestamp(END), periods=4, freq="30D")
    macro = {
        "UNEMPLOYMENT": pd.Series(values, index=dates),
        "YIELD_CURVE": pd.Series([spread], index=[pd.Timestamp(END)]),
    }
    assert cycle_context(macro, END)["phase"] == phase
    assert (
        sum(
            r["cycle_bonus"] > 0
            for r in score_sectors(demo_prices(END), macro, END)["ranking"]
        )
        == 5
    )


def test_stale_macro():
    assert cycle_context(demo_macro(END), date(2025, 6, 1))["phase"] == "unknown"


def test_api_demo():
    client = TestClient(app)
    for endpoint in ("health", "prices", "macro", "analysis"):
        response = client.get(
            f"/api/{endpoint}", params={"mode": "demo", "as_of_date": str(END)}
        )
        assert response.status_code == 200, response.text
    body = client.get(
        "/api/analysis", params={"mode": "demo", "as_of_date": str(END)}
    ).json()
    assert len(body["ranking"]) == 11 and len(body["prices"]) == 12
    assert body["ai"]["status"] == "disabled" and body["updated_at"]


def test_api_errors_no_key():
    client = TestClient(app)
    for value in ("bad", "1998-01-01", str(datetime.now(UTC).date())):
        assert (
            client.get("/api/analysis", params={"as_of_date": value}).status_code == 422
        )
    assert client.get("/api/analysis?mode=bad").status_code == 422
    with patch.dict("os.environ", {}, clear=True):
        assert client.get("/api/macro").json()["status"] == "unavailable"
    with patch("app.main.fetch_sector_prices", side_effect=RuntimeError("secret")):
        response = client.get("/api/analysis")
        assert response.status_code == 503 and "secret" not in response.text


def test_live_api_without_key():
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("app.main.fetch_sector_prices", return_value=demo_prices(END)),
    ):
        response = TestClient(app).get("/api/analysis", params={"as_of_date": str(END)})
    assert response.status_code == 200
    assert response.json()["cycle"]["phase"] == "unknown"
    assert response.json()["macro"]["status"] == "unavailable"
