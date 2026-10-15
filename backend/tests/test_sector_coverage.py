from datetime import UTC, datetime, timedelta

from app.config import SECTOR_TICKERS
from app.services.sectors import GROUPS, market_state, sector_watchlist


def report(mode="live", age=0):
    now = datetime.now(UTC)
    return {
        "id": "saved",
        "mode": mode,
        "price_date": (now.date() - timedelta(days=age)).isoformat(),
        "updated_at": now.isoformat(),
    }


def row(short, long, absolute=2):
    return {
        "ticker": "XLK",
        "relative_20d": short,
        "relative_60d": long,
        "absolute_20d": absolute,
    }


def test_all_major_sectors_and_distinct_subindustries():
    items = sector_watchlist([])
    assert {w["ticker"] for w in items if w["parent"] is None} == set(SECTOR_TICKERS)
    assert len(items) == len({w["ticker"] for w in items}) == 15
    assert {"ITB", "SOXX", "KRE", "IYT"} == {w["ticker"] for w in items if w["parent"]}
    assert all(w["bottom_status"] == "尚未确认筑底" for w in items)


def test_price_groups_cover_hot_cooling_recovering_and_weak():
    today = datetime.now(UTC).date()
    expectations = [
        (row(4, 10, 8), "强势升温"),
        (row(1, 5), "强势延续"),
        (row(-1, 5), "强势降温"),
        (row(1, -5), "弱势修复"),
        (row(-1, -5), "持续走弱"),
        (row(0, 0), "中性震荡"),
    ]
    for value, expected in expectations:
        state = market_state(value, report(), today)
        assert state["group"] == expected and state["group"] in GROUPS
        assert state["metrics"]["relative_20d"] == value["relative_20d"]
    assert market_state(row(3, 10, 5), report(), today)["group"] == "强势升温"


def test_stale_demo_missing_and_future_reports_are_not_classified():
    today = datetime.now(UTC).date()
    for saved in [report("demo"), report(age=8), report(age=-1), None]:
        assert market_state(row(5, 9, 10), saved, today)["group"] == "数据不足"
    old = report()
    old["updated_at"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    assert market_state(row(5, 9, 10), old, today)["metrics"] is None


def test_subindustry_does_not_inherit_parent_price_state():
    saved = report()
    saved["ranking"] = [row(4, 10, 8)]
    items = sector_watchlist([], saved)
    assert (
        next(w for w in items if w["ticker"] == "XLK")["market"]["group"] == "强势升温"
    )
    assert (
        next(w for w in items if w["ticker"] == "SOXX")["market"]["group"] == "数据不足"
    )


def test_invalid_price_values_do_not_create_hot_sector():
    today = datetime.now(UTC).date()
    assert (
        market_state(row(float("nan"), 10, 8), report(), today)["group"] == "数据不足"
    )
    assert market_state(row(5, float("inf"), 8), report(), today)["metrics"] is None
