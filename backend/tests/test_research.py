"""Research contracts: source failure, calendar time, missing evidence and archives."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.data.research import (
    NY,
    election_events,
    parse_feed,
    parse_fomc,
    parse_ics,
    parse_macro,
)
from app.services import research
from app.services.research import ResearchDesk, cycle_view, signal, watchlist


def test_macro_filters_future_invalid_and_preserves_observation_time():
    row = parse_macro(
        "observation_date,INDPRO\n2026-08-01,100\n2026-09-01,101\n2026-10-01,.\n2027-01-01,900\n",
        "INDPRO",
        date(2026, 10, 15),
    )
    assert row["value"] == 101 and row["observation_date"] == "2026-09-01"
    assert row["publication_time"] is None and row["status"] == "available"
    stale = parse_macro(
        "observation_date,INDPRO\n2025-01-01,100\n", "INDPRO", date(2026, 10, 15)
    )
    assert stale["status"] == "stale"
    with pytest.raises(ValueError):
        parse_macro("<html>not a CSV</html>", "INDPRO", date(2026, 10, 15))


def test_ics_folded_lines_dst_utc_and_all_day():
    ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Employment Situa
 tion
DTSTART;TZID=US-Eastern:20261106T083000
URL:https://www.bls.gov/news.release/empsit.htm
END:VEVENT
BEGIN:VEVENT
SUMMARY:Consumer Price Index
DTSTART:20261014T123000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Personal Income and Outlays
DTSTART;VALUE=DATE:20261030
END:VEVENT
END:VCALENDAR"""
    rows = parse_ics(ics, "BLS", "https://www.bls.gov/schedule/")
    assert rows[0]["starts_at"] == "2026-11-06T08:30:00-05:00"
    assert rows[0]["category"] == "非农就业"
    assert rows[1]["starts_at"] == "2026-10-14T08:30:00-04:00"
    assert rows[2]["time_confirmed"] is False
    assert all(r["consensus"] is None and r["actual"] is None for r in rows)


def test_feed_topic_provenance_and_unsafe_link():
    xml = """<rss><channel><item><title>Oil prices rise as conflict grows</title><link>https://example.com/a</link><pubDate>Thu, 15 Oct 2026 12:00:00 GMT</pubDate></item><item><title>War news</title><link>javascript:alert(1)</link><pubDate>Thu, 15 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Future war</title><link>https://example.com/b</link><pubDate>Thu, 15 Oct 2027 12:00:00 GMT</pubDate></item></channel></rss>"""
    rows = parse_feed(xml, "BBC 国际", "2026-10-15T13:00:00+00:00")
    assert len(rows) == 1 and rows[0]["topics"] == ["地缘政治", "通胀与能源"]
    assert "条件假设" in rows[0]["verification"]


def test_fomc_parser_requires_official_structure():
    html = """<div class="panel"><div><h4>2027 FOMC Meetings</h4></div><div class="fomc-meeting"><div class="fomc-meeting__month">March</div><div class="fomc-meeting__date">16-17*</div></div></div>"""
    row = parse_fomc(html)[0]
    assert row["starts_at"].startswith("2027-03-17") and "SEP" in row["title"]
    assert row["time_confirmed"] is False
    with pytest.raises(ValueError):
        parse_fomc("<h4>Unrelated content</h4>")


def test_elections_midterm_and_presidential_dates():
    rows = election_events(date(2026, 10, 15))
    assert rows[0]["starts_at"].startswith("2026-11-03")
    assert rows[1]["starts_at"].startswith("2028-11-07")
    assert "中期" in rows[0]["title"] and "总统" in rows[1]["title"]


def macro_row(key, values, dates=None):
    points = [
        {"date": day, "value": v}
        for day, v in zip(
            dates or [f"2025-{i + 1:02d}-01" for i in range(len(values))], values
        )
    ]
    return {
        "id": key,
        "name": key,
        "unit": "index",
        "value": values[-1],
        "observation_date": points[-1]["date"],
        "status": "available",
        "url": "https://fred.stlouisfed.org",
        "points": points,
    }


def test_cycle_never_invents_missing_or_stale_evidence():
    empty = cycle_view([])
    assert empty["confidence"] == "不足" and empty["growth"] == []
    row = macro_row("INDPRO", [100, 101, 102, 103, 104, 105, 106])
    row["status"] = "stale"
    assert signal(row, 3) is None and cycle_view([row])["coverage"] == 0
    assert all(w["bottom_status"] == "尚未确认筑底" for w in watchlist([]))
    gap = macro_row(
        "INDPRO",
        [100, 101, 102, 103],
        ["2025-01-01", "2025-02-01", "2025-04-01", "2025-06-01"],
    )
    assert signal(gap, 3) is None


def test_cycle_exposes_growth_conflict_and_inflation_math():
    dates = [f"{2024 + i // 12}-{i % 12 + 1:02d}-01" for i in range(13)]
    rows = [
        macro_row("INDPRO", [100 + i for i in range(13)], dates),
        macro_row("PCEC96", [100 - i for i in range(13)], dates),
    ]
    rows += [
        macro_row(k, [100 * (1.002**i) for i in range(13)], dates)
        for k in ["CPIAUCSL", "PCEPILFE"]
    ]
    view = cycle_view(rows)
    assert any("方向不一致" in c for c in view["contradictions"])
    assert view["inflation"][0]["annualized_3m"] == round(((1.002**12) - 1) * 100, 2)


def test_schedule_slots_use_new_york_and_dst(tmp_path):
    desk = ResearchDesk(str(tmp_path / "journal.db"))
    assert (
        desk.slot(datetime(2026, 11, 2, 12, 59, tzinfo=UTC))
        == "2026-11-01T17:00:00-05:00"
    )
    assert (
        desk.slot(datetime(2026, 11, 2, 13, 0, tzinfo=UTC))
        == "2026-11-02T08:00:00-05:00"
    )
    assert (
        desk.slot(datetime(2026, 10, 15, 21, 0, tzinfo=UTC))
        == "2026-10-15T17:00:00-04:00"
    )


def test_refresh_archive_dedup_and_failure_preservation(tmp_path, monkeypatch):
    desk = ResearchDesk(str(tmp_path / "journal.db"))
    now = datetime.now(UTC)
    day = now.astimezone(NY).date()

    def resource(url, parser):
        if "fredgraph" in url:
            key = url.split("id=")[1].split("&")[0]
            return parse_macro(f"observation_date,{key}\n{day},100\n", key, day)
        if "rss" in url or "feed" in url or ".xml" in url:
            return [
                {
                    "id": "same-title",
                    "published_at": now.isoformat(),
                    "title": "Oil prices",
                    "url": "https://example.com",
                    "source": "test",
                }
            ]
        return [
            {
                "id": url,
                "starts_at": f"{day}T08:30:00-04:00",
                "title": "test",
                "importance": "高",
            }
        ]

    monkeypatch.setattr(research, "fetch_resource", resource)
    desk.refresh()
    first = desk.history()[0]["id"]
    assert len(desk.view()["news"]) == 1
    assert len(desk.report(first)["input_resources"]) == len(desk.view()["sources"])
    assert desk.state("slot") == desk.slot(datetime.now(UTC))
    monkeypatch.setattr(
        research,
        "fetch_resource",
        lambda *args: (_ for _ in ()).throw(ConnectionError("private secret")),
    )
    desk.refresh()
    view = desk.view()
    assert len(view["indicators"]) == len(research.SERIES)
    assert view["cycle"]["coverage"] == 0
    assert all(s["status"] == "error" for s in view["sources"])
    assert len(desk.history()) == 1
    assert "private secret" not in json.dumps(view)
    assert desk.report(first)["cycle"]["coverage"] > 0
    assert not desk.active


def test_source_cache_expiry_and_calendar_preservation(tmp_path):
    desk = ResearchDesk(str(tmp_path / "journal.db"))
    old = (datetime.now(UTC) - timedelta(hours=31)).isoformat()
    row = macro_row("INDPRO", [100, 101, 102, 103])
    with desk.connect() as db:
        db.execute(
            "INSERT INTO research_resources VALUES (?,?,?,?,NULL)",
            ("macro:INDPRO", json.dumps(row), old, old),
        )
    assert desk.view()["cycle"]["coverage"] == 0
    assert desk.view()["indicators"][0]["status"] == "stale"


def test_research_api_reads_do_not_fetch_and_archive_404(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTORPULSE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("SECTORPULSE_RESEARCH_AUTO", "0")
    monkeypatch.setattr(
        research, "fetch_text", lambda *args: pytest.fail("GET must not fetch")
    )
    from app.main import app

    with TestClient(app) as client:
        result = client.get("/api/research")
        assert (
            result.status_code == 200 and result.json()["cycle"]["confidence"] == "不足"
        )
        assert client.get("/api/research/reports").json() == []
        assert client.get("/api/research/reports/999").status_code == 404


def test_macro_uses_calendar_endpoints_not_row_offsets():
    row = macro_row(
        "CPIAUCSL",
        [100, 102, 103, 104],
        ["2025-09-01", "2026-03-01", "2026-06-01", "2026-09-01"],
    )
    assert signal(row, 12) == pytest.approx(4.0)
    assert signal(row, 3) == pytest.approx((104 / 103 - 1) * 100)


def test_policy_drivers_compare_observation_dates_and_reject_stale():
    row = macro_row("DFF", [4.5, 4.0], ["2026-07-01", "2026-10-01"])
    driver = research.macro_drivers([row])[0]
    assert driver["state"] == "近期下行"
    row["status"] = "stale"
    assert research.macro_drivers([row])[0]["state"] == "证据缺失"


def test_regional_personal_income_is_not_national_pce():
    from app.data.research import event_context

    assert event_context("GDP by County and Personal Income by County, 2025")[0:2] == (
        "地区经济",
        "中",
    )
    assert event_context("Personal Income and Outlays, September 2026")[0:2] == (
        "PCE／收入与消费",
        "高",
    )


def test_news_does_not_find_war_inside_towards():
    xml = "<rss><channel><item><title>Drift towards extremism not inevitable</title><link>https://example.com/a</link><pubDate>Thu, 15 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>"
    assert parse_feed(xml, "BBC 国际", "2026-10-15T13:00:00+00:00") == []
