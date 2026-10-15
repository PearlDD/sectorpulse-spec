"""Local daily research journal. Missing or stale evidence never becomes a signal."""

import json
import logging
import sqlite3
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from app.data.research import (
    BEA_URL,
    BLS_URL,
    FEEDS,
    FOMC_URL,
    NY,
    SERIES,
    classify_title,
    election_events,
    event_context,
    fetch_text,
    parse_feed,
    parse_fomc,
    parse_ics,
    parse_macro,
)
from app.services.sectors import GROUPS, sector_watchlist

log = logging.getLogger(__name__)
METHOD = "us-cycle-evidence-v1"


def fetch_resource(url: str, parser: Callable[[str], Any]) -> Any:
    return parser(fetch_text(url))


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def signal(row: dict | None, lag: int) -> float | None:
    if row is None or row.get("status") != "available":
        return None
    points = row["points"]
    if len(points) < 2:
        return None
    monthly = row["id"] not in {"DFF", "T10Y2Y", "BAMLH0A0HYM2", "ICSA", "WALCL"}
    new = points[-1]["value"]
    if monthly:
        end = date.fromisoformat(points[-1]["date"])
        month_index = end.year * 12 + end.month - 1 - lag
        target = f"{month_index // 12:04d}-{month_index % 12 + 1:02d}"
        match = next((p for p in points if p["date"][:7] == target), None)
        if match is None:
            return None
        old = match["value"]
    else:
        old = points[-lag - 1]["value"]
    return (new / old - 1) * 100 if old else None


def macro_drivers(rows: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in rows if r.get("status") == "available"}
    results = []
    for key, label, interpretation in [
        ("DFF", "政策利率", "利率下降需区分通胀改善与需求恶化；不自动视为利好。"),
        (
            "BAMLH0A0HYM2",
            "信用环境",
            "利差收窄通常代表融资压力缓和，但不能替代银行坏账与放贷标准。",
        ),
        (
            "WALCL",
            "央行资产负债表",
            "总资产变化不等于净流动性，尚未纳入财政账户与逆回购。",
        ),
        (
            "T10Y2Y",
            "收益率曲线",
            "曲线走陡需区分长端升息与短端降息，不能单独判断复苏。",
        ),
    ]:
        row = by_id.get(key)
        if row is None:
            results.append(
                {
                    "name": label,
                    "state": "证据缺失",
                    "evidence": "缺失或过期资料不参与判断",
                    "interpretation": interpretation,
                    "url": f"https://fred.stlouisfed.org/series/{key}",
                }
            )
            continue
        target = date.fromisoformat(row["observation_date"]) - timedelta(days=91)
        past = [p for p in row["points"] if date.fromisoformat(p["date"]) <= target]
        old = past[-1] if past else None
        if old is None or (target - date.fromisoformat(old["date"])).days > 14:
            state, evidence = "历史不足", "无法匹配约 3 个月前的比较值"
        else:
            delta = row["value"] - old["value"]
            epsilon = 0.05 if key != "WALCL" else 1000
            state = (
                "近期上行"
                if delta > epsilon
                else "近期下行"
                if delta < -epsilon
                else "大致持平"
            )
            evidence = f"{old['date']}：{old['value']:,.3f} → {row['observation_date']}：{row['value']:,.3f} {row['unit']}"
        results.append(
            {
                "name": label,
                "state": state,
                "evidence": evidence,
                "interpretation": interpretation,
                "url": row["url"],
            }
        )
    return results


def cycle_view(rows: list[dict]) -> dict:
    available = {r["id"]: r for r in rows if r.get("status") == "available"}
    growth = []
    for key in ("INDPRO", "PCEC96"):
        row = available.get(key)
        current, six = signal(row, 3), signal(row, 6)
        if row is not None and current is not None and six is not None:
            previous = ((1 + six / 100) / (1 + current / 100) - 1) * 100
            growth.append(
                {
                    "id": key,
                    "name": row["name"],
                    "change_3m": round(current, 3),
                    "acceleration_pp": round(current - previous, 3),
                    "observation_date": row["observation_date"],
                    "url": row["url"],
                }
            )
    inflation = []
    for key in ("CPIAUCSL", "PCEPILFE"):
        row = available.get(key)
        three, six, year = signal(row, 3), signal(row, 6), signal(row, 12)
        if (
            row is not None
            and three is not None
            and six is not None
            and year is not None
        ):
            previous = (1 + six / 100) / (1 + three / 100) - 1
            inflation.append(
                {
                    "name": row["name"],
                    "annualized_3m": round(((1 + three / 100) ** 4 - 1) * 100, 2),
                    "previous_3m": round(((1 + previous) ** 4 - 1) * 100, 2),
                    "yoy": round(year, 2),
                    "url": row["url"],
                }
            )
    unemployment = available.get("UNRATE")
    u_change = None
    u_signal = signal(unemployment, 3)
    if unemployment is not None and u_signal is not None:
        u_change = unemployment["value"] - unemployment["value"] / (1 + u_signal / 100)
    payroll = signal(available.get("PAYEMS"), 3)
    credit = available.get("BAMLH0A0HYM2")
    stress = credit is not None and credit["value"] >= 5
    recession_evidence = (u_change is not None and u_change >= 0.3) or (
        payroll is not None and payroll < 0
    )
    label, alternative = "证据不足，暂不判断周期", "等待增长、通胀和就业数据覆盖"
    if len(growth) == 2 and len(inflation) == 2:
        level = sum(x["change_3m"] for x in growth) / 2
        accel = sum(x["acceleration_pp"] for x in growth) / 2
        if level < 0:
            label = "收缩倾向" if recession_evidence else "增长走弱，收缩待确认"
            alternative = "短暂调整后恢复增长；需消费、生产和就业共同验证"
        elif accel > 0.1:
            label = "增长再加速倾向" if recession_evidence else "扩张／复苏倾向"
            alternative = "库存或单月波动带来的假性改善；就业与信用可能尚未跟上"
        elif accel < -0.1:
            label = "扩张放缓倾向"
            alternative = "软着陆或继续恶化，取决于就业、实际消费与信用条件"
        else:
            label, alternative = (
                "增长平稳，转折不明确",
                "维持扩张或转向放缓，尚缺连续证据",
            )
    missing = [meta[0] for key, meta in SERIES.items() if key not in available]
    contradictions = []
    if growth and min(x["change_3m"] for x in growth) < 0 < max(
        x["change_3m"] for x in growth
    ):
        contradictions.append(
            "工业生产与实际消费方向不一致，不能强行归为同一个周期阶段。"
        )
    if recession_evidence:
        contradictions.append("就业侧出现走弱信号，应检验增长改善是否具有持续性。")
    if stress:
        contradictions.append(
            "高收益债利差达到规则压力阈值 5 个百分点；与增长信号交叉核验。"
        )
    if inflation and any(i["annualized_3m"] > i["previous_3m"] for i in inflation):
        contradictions.append("至少一项通胀动量回升，增长改善未必允许政策宽松。")
    if not contradictions:
        contradictions.append(
            "当前规则未发现明显方向冲突；不代表不存在反证或外生风险。"
        )
    return {
        "label": label,
        "alternative": alternative,
        "growth": growth,
        "drivers": macro_drivers(rows),
        "inflation": inflation,
        "missing": missing,
        "calculation_gaps": [
            r["name"]
            for r in rows
            if r["id"] in {"INDPRO", "PCEC96", "CPIAUCSL", "PCEPILFE"}
            and (
                signal(r, 3) is None
                or signal(r, 6) is None
                or (r["id"] in {"CPIAUCSL", "PCEPILFE"} and signal(r, 12) is None)
            )
        ],
        "contradictions": contradictions,
        "confidence": "不足"
        if len(growth) < 2 or len(inflation) < 2
        else "有限（规则判断，未经概率校准）",
        "coverage": len(available),
        "expected": len(SERIES),
        "method": "工业生产与实际消费的 3 个月变化及相对前 3 个月的加速度；CPI／核心 PCE 通胀动量；就业与信用反证。阈值为可审阅启发式，非 NBER 衰退认定。",
        "horizon": "6–18 个月",
        "unemployment_change_3m_pp": round(u_change, 2)
        if u_change is not None
        else None,
    }


def watchlist(
    rows: list[dict], report: dict | None = None, today: date | None = None
) -> list[dict]:
    return sector_watchlist(rows, report, today)


class ResearchDesk:
    def __init__(self, path: str):
        self.path = path
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.active = False
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS research_resources (
                    name TEXT PRIMARY KEY, payload TEXT NOT NULL, last_success TEXT NOT NULL,
                    last_attempt TEXT NOT NULL, error TEXT
                );
                CREATE TABLE IF NOT EXISTS research_news (
                    id TEXT PRIMARY KEY, published_at TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS research_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def state(self, key: str) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT value FROM research_state WHERE key=?", (key,)
            ).fetchone()
        return row[0] if row else None

    def set_state(self, key: str, value: str):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO research_state VALUES (?,?)", (key, value)
            )

    def start(self):
        self.thread = threading.Thread(
            target=self.loop, daemon=True, name="macro-daily-scheduler"
        )
        self.thread.start()

    def slot(self, current: datetime) -> str:
        local = current.astimezone(NY)
        anchor = local.replace(
            hour=17 if local.hour >= 17 else 8, minute=0, second=0, microsecond=0
        )
        if local.hour < 8:
            anchor = (local - timedelta(days=1)).replace(
                hour=17, minute=0, second=0, microsecond=0
            )
        return anchor.isoformat()

    def loop(self):
        while not self.stop.is_set():
            try:
                current = datetime.now(UTC)
                slot = self.slot(current)
                last_attempt = self.state("attempt")
                retry_due = (
                    last_attempt is None
                    or (current - datetime.fromisoformat(last_attempt)).total_seconds()
                    > 1800
                )
                if self.state("slot") != slot and retry_due:
                    self.refresh()
            except Exception:  # noqa: BLE001 - keep daily scheduler alive without leaking provider text
                log.warning("Daily research refresh failed; retry later")
            self.stop.wait(30)

    def request_refresh(self) -> bool:
        with self.lock:
            if self.active:
                return False
            self.active = True
        threading.Thread(
            target=self.refresh,
            kwargs={"reserved": True},
            daemon=True,
            name="macro-manual-refresh",
        ).start()
        return True

    def refresh(self, reserved: bool = False):
        if not reserved:
            with self.lock:
                if self.active:
                    return
                self.active = True
        started = utcnow()
        self.set_state("attempt", started)
        today = datetime.now(NY).date()
        tasks: dict[str, tuple[str, Callable[[str], Any]]] = {}
        for key in SERIES:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={key}&cosd={(today - timedelta(days=850)).isoformat()}"
            tasks[f"macro:{key}"] = (
                url,
                partial(parse_macro, series_id=key, today=today),
            )
        for name, url in FEEDS.items():
            tasks[f"news:{name}"] = (
                url,
                partial(parse_feed, source=name, fetched_at=started),
            )
        tasks["calendar:BLS"] = (
            BLS_URL,
            partial(parse_ics, source="BLS", source_url=BLS_URL),
        )
        tasks["calendar:BEA"] = (
            BEA_URL,
            partial(parse_ics, source="BEA", source_url=BEA_URL),
        )
        tasks["calendar:FOMC"] = (FOMC_URL, parse_fomc)
        succeeded = 0
        try:
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {
                    pool.submit(fetch_resource, url, parser): name
                    for name, (url, parser) in tasks.items()
                }
                for future in as_completed(futures):
                    name = futures[future]
                    if self.stop.is_set():
                        return
                    try:
                        payload = future.result()
                        with self.connect() as db:
                            db.execute(
                                "INSERT OR REPLACE INTO research_resources VALUES (?,?,?,?,NULL)",
                                (
                                    name,
                                    json.dumps(payload, ensure_ascii=False),
                                    utcnow(),
                                    started,
                                ),
                            )
                            if name.startswith("news:"):
                                for item in payload:
                                    db.execute(
                                        "INSERT OR IGNORE INTO research_news VALUES (?,?,?)",
                                        (
                                            item["id"],
                                            item["published_at"],
                                            json.dumps(item, ensure_ascii=False),
                                        ),
                                    )
                        succeeded += 1
                    except Exception as exc:  # noqa: BLE001 - retain good resource; safe error code only
                        with self.connect() as db:
                            db.execute(
                                "INSERT INTO research_resources VALUES (?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET last_attempt=excluded.last_attempt,error=excluded.error",
                                (name, "null", "", started, type(exc).__name__),
                            )
            view = self.view(include_history=False)
            if succeeded:
                view["refreshing"] = False
                view["last_success"] = utcnow()
                with self.connect() as db:
                    view["input_resources"] = [
                        dict(row)
                        for row in db.execute(
                            "SELECT * FROM research_resources ORDER BY name"
                        )
                    ]
                with self.connect() as db:
                    db.execute(
                        "INSERT INTO research_reports(created_at,payload) VALUES (?,?)",
                        (utcnow(), json.dumps(view, ensure_ascii=False)),
                    )
                self.set_state("success", utcnow())
            if succeeded == len(tasks):
                self.set_state("slot", self.slot(datetime.now(UTC)))
        finally:
            with self.lock:
                self.active = False

    def view(self, include_history: bool = True) -> dict:
        current = datetime.now(UTC)
        today = current.astimezone(NY).date()
        with self.connect() as db:
            resources = [
                dict(row)
                for row in db.execute("SELECT * FROM research_resources ORDER BY name")
            ]
            news = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT payload FROM research_news ORDER BY published_at DESC LIMIT 400"
                )
            ]
            market_row = (
                db.execute(
                    "SELECT payload FROM runs WHERE mode='live' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='runs'"
                ).fetchone()
                else None
            )
            market_report = json.loads(market_row[0]) if market_row else None
            last = (
                db.execute(
                    "SELECT id,created_at,payload FROM research_reports ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if include_history
                else None
            )
        classified_news = []
        for item in news:
            matches = classify_title(item["title"])
            if matches:
                item["topics"] = [m[0] for m in matches]
                item["transmission"] = matches[0][1]
                classified_news.append(item)
        news = classified_news
        macros, events, sources = [], election_events(today), []
        for row in resources:
            payload = json.loads(row["payload"])
            age_hours = (
                (current - datetime.fromisoformat(row["last_success"])).total_seconds()
                / 3600
                if row["last_success"]
                else None
            )
            stale = age_hours is None or age_hours > 30
            status = "error" if row["error"] else "stale" if stale else "available"
            sources.append(
                {
                    "name": row["name"],
                    "status": status,
                    "last_success": row["last_success"] or None,
                    "last_attempt": row["last_attempt"],
                    "error": row["error"],
                }
            )
            if row["name"].startswith("macro:"):
                if payload:
                    payload["fetched_at"] = row["last_success"]
                    payload["age_days"] = (
                        today - date.fromisoformat(payload["observation_date"])
                    ).days
                    payload["status"] = (
                        "stale"
                        if payload["age_days"] > SERIES[payload["id"]][3]
                        else "available"
                    )
                    if stale or row["error"]:
                        payload["status"] = "stale"
                    macros.append(payload)
            elif row["name"].startswith("calendar:") and payload:
                for event in payload:
                    if row["name"] in {"calendar:BLS", "calendar:BEA"}:
                        event["category"], event["importance"], event["watch"] = (
                            event_context(event["title"])
                        )
                    event["verified_at"] = row["last_success"]
                    event["source_stale"] = stale or bool(row["error"])
                events.extend(payload)
        # Sources not yet attempted are visible, including at first launch.
        expected_names = [
            *(f"macro:{key}" for key in SERIES),
            *(f"news:{name}" for name in FEEDS),
            "calendar:BLS",
            "calendar:BEA",
            "calendar:FOMC",
        ]
        for name in expected_names:
            if not any(s["name"] == name for s in sources):
                sources.append(
                    {
                        "name": name,
                        "status": "pending",
                        "last_success": None,
                        "last_attempt": None,
                        "error": None,
                    }
                )
        cutoff = (today - timedelta(days=7)).isoformat()
        events = sorted(
            {
                e["id"]: e
                for e in events
                if cutoff
                <= e["starts_at"][:10]
                <= (today + timedelta(days=400)).isoformat()
            }.values(),
            key=lambda e: e["starts_at"],
        )
        previous_cycle = json.loads(last["payload"])["cycle"]["label"] if last else None
        return {
            "method_version": METHOD,
            "as_of": current.isoformat(),
            "timezone": "America/New_York",
            "refreshing": self.active,
            "last_attempt": self.state("attempt"),
            "last_success": self.state("success"),
            "schedule": "美东每天 08:00、17:00；启动补抓；缺失源每 30 分钟重试（服务运行时）",
            "cycle": cycle_view(macros),
            "indicators": [
                {k: v for k, v in r.items() if k != "points"} for r in macros
            ],
            "news": [
                n
                for n in news
                if n["published_at"][:10] >= (today - timedelta(days=30)).isoformat()
            ],
            "events": events,
            "watchlist": watchlist(macros, market_report, today),
            "sector_groups": GROUPS,
            "sector_method": "强势升温：20 日绝对涨幅至少 5%，且超越 SPY 至少 3 个百分点；其余按 20／60 日相对 SPY 正负方向分类。超过 7 天的价格报告不分类，细分行业不借用母板块价格。",
            "sources": sources,
            "previous_cycle": previous_cycle,
            "last_report_id": last["id"] if last else None,
            "limitations": [
                "新闻仅标题与链接，主题按关键词筛选；不是全文事实核验，也未自动纳入周期评分。",
                "当前 FRED 修订值用于当下研究，不支持历史时点回测；数据对应月份不等于发布时间。",
                "尚未接入一致预期、行业订单／库存、盈利预测和估值，不能确认超预期、低谷或买点。",
                "停机期间无法采集；启动仅补抓来源仍保留的信息，无法保证补齐所有历史新闻。",
                "日历覆盖 BLS、BEA、FOMC 与联邦选举；ISM、国债发行、公司财报等尚未接入。",
            ],
        }

    def history(self) -> list[dict]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,created_at FROM research_reports ORDER BY id DESC LIMIT 30"
                )
            ]

    def report(self, report_id: int) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM research_reports WHERE id=?", (report_id,)
            ).fetchone()
        if row is None:
            raise KeyError(report_id)
        return json.loads(row[0])

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(2)
