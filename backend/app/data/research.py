"""Current-vintage macro, attributed RSS and official calendars. No LLM input."""

import calendar
import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from curl_cffi import requests

NY = ZoneInfo("America/New_York")
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BLS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BEA_URL = "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics"
SERIES = {
    "GDPC1": ("实际 GDP", "增长", "十亿美元／年化", 220),
    "INDPRO": ("工业生产", "增长", "指数", 80),
    "PCEC96": ("实际个人消费", "增长", "十亿美元", 80),
    "PAYEMS": ("非农就业", "就业", "千人", 80),
    "UNRATE": ("失业率", "就业", "%", 80),
    "ICSA": ("首次申领失业金", "就业", "人", 21),
    "CPIAUCSL": ("CPI 物价指数", "通胀", "指数", 80),
    "PCEPILFE": ("核心 PCE 物价指数", "通胀", "指数", 80),
    "DFF": ("联邦基金有效利率", "政策利率", "%", 10),
    "T10Y2Y": ("10 年－2 年国债利差", "利率曲线", "百分点", 10),
    "BAMLH0A0HYM2": ("高收益债信用利差", "信用", "百分点", 10),
    "WALCL": ("美联储总资产", "流动性", "百万美元", 21),
    "HOUST": ("新屋开工", "住房", "千套／年化", 80),
}
FEEDS = {
    "美联储公告": "https://www.federalreserve.gov/feeds/press_all.xml",
    "BLS 发布": "https://www.bls.gov/feed/bls_latest.rss",
    "BEA 发布": "https://www.bea.gov/news/blog/feed",
    "BBC 国际": "https://feeds.bbci.co.uk/news/world/rss.xml",
}
# Conditional transmission hypotheses, never claims extracted from an article.
CHANNELS = [
    (
        "地缘政治",
        r"war|iran|israel|ukrain\w*|russia\w*|conflict\w*|missiles?|military|ceasefire|nato",
        "冲突若影响能源供给或运输 → 成本与通胀风险 → 关注能源、运输和可选消费；先核实实际供给变化。",
    ),
    (
        "贸易政策",
        r"tariffs?|trade|sanctions?|export controls?",
        "若关税或出口限制生效 → 采购成本及海外收入变化 → 关注半导体、工业与零售；需核实政策范围。",
    ),
    (
        "货币政策",
        r"federal reserve|fomc|interest rate|monetary|rate cut|rate hike",
        "若政策路径改变 → 融资成本与估值折现率变化 → 关注住房、银行和长久期资产；降息不等于经济改善。",
    ),
    (
        "财政与选举",
        r"election|congress|budget|tax|shutdown|debt ceiling|fiscal",
        "若立法与预算落地 → 税后盈利、政府订单及发债变化 → 关注相关行业；不把竞选承诺当成已实施政策。",
    ),
    (
        "通胀与能源",
        r"inflation|consumer price|pce|oil|energy|opec",
        "若价格压力持续 → 利率预期与企业利润率变化 → 关注能源、消费和公用事业；需区分需求与供给冲击。",
    ),
    (
        "增长与就业",
        r"employment|jobs|payroll|gdp|economy|economic|manufactur\w*|retail",
        "若需求或就业趋势改变 → 销售与信用质量变化 → 关注工业、消费和银行；以数据细项和修正验证。",
    ),
]


def fetch_text(url: str) -> str:
    response = requests.get(url, impersonate="chrome", timeout=18, allow_redirects=True)
    response.raise_for_status()
    if len(response.content) > 3_000_000:
        raise ValueError("Provider response too large")
    return response.text.lstrip("\ufeff")


def safe_url(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme in {"http", "https"} and parsed.netloc and not parsed.username:
        return value.strip()
    return None


def text_only(value: str) -> str:
    return " ".join(BeautifulSoup(value, "html.parser").get_text(" ").split())[:500]


def parse_macro(content: str, series_id: str, today: date) -> dict:
    name, group, unit, max_age = SERIES[series_id]
    rows: list[dict] = []
    for row in csv.DictReader(io.StringIO(content)):
        try:
            day = date.fromisoformat(row.get("observation_date", row.get("DATE", "")))
            value = float(row[series_id])
            if day <= today and value == value and abs(value) < 1e16:
                rows.append({"date": day.isoformat(), "value": value})
        except (KeyError, ValueError, TypeError):
            continue
    rows = sorted({x["date"]: x for x in rows}.values(), key=lambda x: x["date"])
    if not rows:
        raise ValueError("No usable observations")
    last = rows[-1]
    age = (today - date.fromisoformat(last["date"])).days
    return {
        "id": series_id,
        "name": name,
        "group": group,
        "unit": unit,
        "value": last["value"],
        "observation_date": last["date"],
        "age_days": age,
        "status": "stale" if age > max_age else "available",
        "points": rows[-600:],
        "url": f"https://fred.stlouisfed.org/series/{series_id}",
        "vintage": "当前可见修订值；不是历史时点数据",
        "publication_time": None,
    }


def classify_title(title: str) -> list[tuple[str, str]]:
    return [
        (name, hypothesis)
        for name, pattern, hypothesis in CHANNELS
        if re.search(r"\b(?:" + pattern + r")\b", title, re.I)
    ]


def parse_feed(content: str, source: str, fetched_at: str) -> list[dict]:
    root = ET.fromstring(content)
    result = []
    for item in root.findall(".//item")[:100]:
        title = text_only(item.findtext("title", ""))
        url = safe_url(item.findtext("link", ""))
        stamp = item.findtext("pubDate", "")
        try:
            published = parsedate_to_datetime(stamp)
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
            published = published.astimezone(UTC)
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            not title
            or not url
            or published > datetime.fromisoformat(fetched_at) + timedelta(minutes=5)
        ):
            continue
        matches = classify_title(title)
        if not matches:
            continue
        result.append(
            {
                "id": hashlib.sha256(
                    re.sub(r"\W+", "", title.lower()).encode()
                ).hexdigest(),
                "title": title,
                "url": url,
                "source": source,
                "published_at": published.isoformat(),
                "fetched_at": fetched_at,
                "topics": [m[0] for m in matches],
                "transmission": matches[0][1],
                "evidence_level": "官方发布标题"
                if source != "BBC 国际"
                else "媒体报道标题",
                "verification": "未读取全文；传导路径为条件假设，未计入周期评分",
            }
        )
    return result


def event_context(title: str) -> tuple[str, str, str]:
    title = title.lower()
    if re.search(r"\b(county|state|metropolitan|regional)\b", title):
        return (
            "地区经济",
            "中",
            "地区数据用于交叉验证，不等同于全国 GDP、PCE 或非农发布。",
        )
    if "employment situation" in title:
        return (
            "非农就业",
            "高",
            "看就业增量、失业率、工资及前值修正；强就业也可能延后降息。",
        )
    if "consumer price" in title:
        return (
            "CPI 通胀",
            "高",
            "看核心、住房与服务细项及连续趋势；单月回落不足以确认通胀结束。",
        )
    if (
        "personal income and outlays" in title
        or "personal consumption expenditures" in title
    ):
        return (
            "PCE／收入与消费",
            "高",
            "同时检查核心 PCE 与实际消费，区分需求降温和购买力改善。",
        )
    if "gross domestic" in title or "gdp" in title:
        return (
            "GDP",
            "高",
            "拆分消费、投资、库存和净出口，并检查修订；库存拉动不等于终端需求增强。",
        )
    if "producer price" in title:
        return "PPI", "中", "观察投入成本和向消费价格的传导，不直接等同于企业利润改善。"
    if "job openings" in title:
        return (
            "职位空缺 JOLTS",
            "中",
            "看职位空缺、招聘、离职与裁员，配合非农和申领失业金判断。",
        )
    return (
        "经济发布",
        "中",
        "核对官方发布和修正；市场一致预期尚未接入，不能判定超预期。",
    )


def parse_ics(content: str, source: str, source_url: str) -> list[dict]:
    content = re.sub(r"\r?\n[ \t]", "", content)
    events = []
    for block in content.split("BEGIN:VEVENT")[1:]:
        fields = {}
        for line in block.split("END:VEVENT", 1)[0].splitlines():
            key, separator, value = line.partition(":")
            if separator:
                fields[key] = value
        start_key = next((k for k in fields if k.split(";")[0] == "DTSTART"), None)
        if not start_key or any(k.startswith("RRULE") for k in fields):
            continue  # Unsupported recurrence is never silently assigned one guessed date.
        raw = fields[start_key]
        title = text_only(
            fields.get("SUMMARY", "").replace("\\,", ",").replace("\\n", " ")
        )
        try:
            if len(raw) == 8:
                start = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=NY)
                timed = False
            else:
                fmt = "%Y%m%dT%H%M%SZ" if raw.endswith("Z") else "%Y%m%dT%H%M%S"
                start = datetime.strptime(raw, fmt).replace(tzinfo=NY)
                tzid = re.search(r"TZID=([^;:]+)", start_key)
                zone = (
                    UTC
                    if raw.endswith("Z")
                    else ZoneInfo(
                        {
                            "US-Eastern": "America/New_York",
                            "Eastern Standard Time": "America/New_York",
                        }.get(tzid.group(1), tzid.group(1))
                    )
                    if tzid
                    else NY
                )
                start = start.replace(tzinfo=zone).astimezone(NY)
                timed = True
        except (ValueError, KeyError):
            continue
        category, importance, watch = event_context(title)
        events.append(
            {
                "id": hashlib.sha256(
                    f"{source}:{title}:{start.isoformat()}".encode()
                ).hexdigest(),
                "title": title,
                "category": category,
                "importance": importance,
                "starts_at": start.isoformat(),
                "time_confirmed": timed,
                "source": source,
                "url": safe_url(fields.get("URL", "")) or source_url,
                "watch": watch,
                "consensus": None,
                "actual": None,
                "status": "官方日历，可能调整",
            }
        )
    if not events:
        raise ValueError("Calendar contains no supported events")
    return events


def parse_fomc(content: str) -> list[dict]:
    soup = BeautifulSoup(content, "html.parser")
    result = []
    for heading in soup.find_all("h4"):
        match = re.search(r"(20\d{2}) FOMC Meetings", heading.get_text())
        if not match:
            continue
        panel = heading.find_parent("div", class_="panel")
        if panel is None:
            continue
        for row in panel.select(".fomc-meeting"):
            month_node, day_node = (
                row.select_one(".fomc-meeting__month"),
                row.select_one(".fomc-meeting__date"),
            )
            if not month_node or not day_node:
                continue
            month_name = month_node.get_text(strip=True).split("/")[-1]
            month = next(
                (i for i, name in enumerate(calendar.month_name) if name == month_name),
                None,
            )
            days = re.findall(r"\d+", day_node.get_text())
            if not month or not days or "notation" in day_node.get_text().lower():
                continue
            start = datetime(int(match[1]), month, int(days[-1]), tzinfo=NY)
            result.append(
                {
                    "id": f"fomc-{start.date()}",
                    "title": "FOMC 会议结束"
                    + (" · 经济预测 SEP" if "*" in day_node.get_text() else ""),
                    "category": "美联储议息",
                    "importance": "高",
                    "starts_at": start.isoformat(),
                    "time_confirmed": False,
                    "source": "美联储",
                    "url": FOMC_URL,
                    "watch": "比较政策声明、利率路径、经济预测和发布会；因经济恶化而降息与通胀改善而降息含义不同。",
                    "consensus": None,
                    "actual": None,
                    "status": "官方会议日程；具体发布时间待确认",
                }
            )
    if not result:
        raise ValueError("FOMC calendar format changed")
    return result


def election_events(today: date) -> list[dict]:
    result = []
    for year in range(today.year, today.year + 3):
        if year % 2:
            continue
        first = date(year, 11, 1)
        first_monday = first + timedelta(days=(0 - first.weekday()) % 7)
        day = first_monday + timedelta(days=1)
        result.append(
            {
                "id": f"election-{year}",
                "title": "美国总统及国会选举" if year % 4 == 0 else "美国中期选举",
                "category": "选举与财政",
                "importance": "高",
                "starts_at": datetime.combine(day, datetime.min.time(), NY).isoformat(),
                "time_confirmed": False,
                "source": "联邦选举日期规则",
                "url": "https://www.usa.gov/election-day",
                "watch": "跟踪国会控制权、税收、关税、监管与财政支出；选举结果不等于政策已经落地。",
                "consensus": None,
                "actual": None,
                "status": "按法定日期计算；各州投票时间不同",
            }
        )
    return result
