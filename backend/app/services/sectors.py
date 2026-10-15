"""Complete sector coverage; price-state groups are separate from fundamentals."""

from datetime import UTC, date, datetime
from math import isfinite

# Main sectors use the 11 Select Sector ETF proxies; subindustries stay distinct.
UNIVERSE = [
    (
        "XLB",
        "原材料",
        None,
        "INDPRO",
        "工业需求、金属化工价格、库存与利润率",
        "需求与补库存同步改善可能支持材料盈利。",
        "终端需求下滑、原料成本上涨或新增产能压低价格。",
    ),
    (
        "XLC",
        "通信服务",
        None,
        "PCEC96",
        "广告支出、用户增长、资本开支与自由现金流",
        "广告需求与现金流改善可能支持通信平台及内容行业。",
        "广告预算收缩、用户流失、监管压力或资本开支侵蚀现金流。",
    ),
    (
        "XLE",
        "能源",
        None,
        "CPIAUCSL",
        "原油供需、库存、生产成本与资本纪律",
        "供需趋紧可能支持现金流；地缘事件只有影响实际供给才构成证据。",
        "供给恢复、需求下滑或油价冲高后回落。",
    ),
    (
        "XLF",
        "金融",
        None,
        "BAMLH0A0HYM2",
        "信贷增速、净息差、拨备、资本市场活动与估值",
        "融资条件改善与信用损失可控可能支持金融盈利。",
        "坏账上升、融资成本走高、净息差收缩或交易活动降温。",
    ),
    (
        "XLI",
        "工业",
        None,
        "INDPRO",
        "制造业新订单、订单积压、资本开支与利润率",
        "终端需求和资本开支回升可能带动订单与生产。",
        "仅补库存而终端销售走弱，或成本侵蚀利润。",
    ),
    (
        "XLK",
        "信息技术",
        None,
        "INDPRO",
        "企业 IT 支出、云服务增长、资本开支回报与估值",
        "生产率投资与企业需求可能支持技术盈利，但需核对预期是否过高。",
        "订单放缓、资本开支回报不及预期或估值压缩。",
    ),
    (
        "XLP",
        "必需消费",
        None,
        "PCEC96",
        "销量、提价能力、投入成本与渠道库存",
        "稳定需求和成本回落可能改善现金流与利润率。",
        "消费者转向低价品牌、销量下滑或高估值失去支撑。",
    ),
    (
        "XLRE",
        "房地产",
        None,
        "DFF",
        "融资与再融资成本、出租率、租金和物业类型差异",
        "利率压力缓和且经营现金流稳定可能帮助房地产修复。",
        "再融资困难、空置率攀升或租金与资产价值下调。",
    ),
    (
        "XLU",
        "公用事业",
        None,
        "DFF",
        "电力需求、监管回报、资本开支融资与负债",
        "电力需求与获批投资回报可能支持盈利，需同步核验融资成本。",
        "资本开支超支、融资压力或监管限制回报。",
    ),
    (
        "XLV",
        "医疗保健",
        None,
        "PCEC96",
        "药品管线、专利到期、医疗利用率、医保定价与估值",
        "产品创新与稳定医疗需求可能提供盈利支撑，但行业内分化较大。",
        "临床失败、专利悬崖、成本上涨或支付政策压价。",
    ),
    (
        "XLY",
        "可选消费",
        None,
        "PCEC96",
        "实际消费、消费者信贷拖欠、零售利润率",
        "实际购买力改善且信用压力可控 → 消费盈利可能修复。",
        "就业恶化、拖欠上升或促销扩大。",
    ),
    (
        "ITB",
        "住房建筑",
        "XLY",
        "HOUST",
        "新屋开工、按揭利率、取消订单与建商指引",
        "融资成本下降且新订单止跌 → 住房需求可能恢复。",
        "开工持续下滑、取消订单增加或就业恶化。",
    ),
    (
        "SOXX",
        "半导体",
        "XLK",
        "INDPRO",
        "芯片库存天数、订单／出货、资本开支与盈利预期",
        "库存去化与新订单改善 → 产能利用率及盈利可能转折。",
        "订单再下修、库存重新积压或出口限制扩大。",
    ),
    (
        "KRE",
        "区域银行",
        "XLF",
        "BAMLH0A0HYM2",
        "存款成本、净息差、商业地产敞口与坏账",
        "融资压力缓和且信用损失可控 → 盈利修复才有基础。",
        "存款流失、拨备上升或信用利差持续扩大。",
    ),
    (
        "IYT",
        "运输",
        "XLI",
        "INDPRO",
        "货运量、运价、库存／销售与燃料成本",
        "订单与货运量同步回升可能支持运输需求。",
        "货运量下降、运力过剩或燃料成本侵蚀利润。",
    ),
]
GROUPS = [
    "强势升温",
    "强势延续",
    "强势降温",
    "弱势修复",
    "持续走弱",
    "中性震荡",
    "数据不足",
]

FOCUS = {
    "强势升温": "检验盈利兑现能否支撑近期涨幅，避免只凭热度追涨。",
    "强势延续": "检验领先是否由盈利改善支撑，并跟踪相对动量转弱。",
    "强势降温": "区分正常消化涨幅与盈利趋势恶化，关注预期下修。",
    "弱势修复": "验证价格修复能否得到订单、盈利和现金流的确认。",
    "持续走弱": "先区分周期下行和结构性恶化，寻找止跌证据而非只看便宜。",
    "中性震荡": "观察新的盈利或政策催化，暂不强行赋予趋势。",
    "数据不足": "补齐直接价格和行业数据，再判断热度与经营周期。",
}


def market_state(row: dict | None, report: dict | None, today: date) -> dict:
    unavailable = {
        "group": "数据不足",
        "metrics": None,
        "as_of": None,
        "reason": "缺少新鲜的真实价格报告；不以宏观数据猜测价格热度。",
    }
    if not row or not report or report.get("mode") != "live":
        return unavailable
    try:
        age = (today - date.fromisoformat(report["price_date"])).days
        fetched = datetime.fromisoformat(report["updated_at"])
        cache_age = (datetime.now(UTC) - fetched).total_seconds() / 86400
        if not 0 <= age <= 7 or not 0 <= cache_age <= 7:
            return {
                **unavailable,
                "reason": "价格报告已过期；刷新价格辅助后再判断市场状态。",
            }
        short, long = float(row["relative_20d"]), float(row["relative_60d"])
        absolute = float(row["absolute_20d"])
        if not all(isfinite(value) for value in (short, long, absolute)):
            return unavailable
    except (KeyError, ValueError, TypeError):
        return unavailable
    if absolute >= 5 and short >= 3:
        group = "强势升温"
    elif short >= 0 and long > 0:
        group = "强势延续"
    elif short < 0 and long > 0:
        group = "强势降温"
    elif short > 0 and long <= 0:
        group = "弱势修复"
    elif short < 0 and long <= 0:
        group = "持续走弱"
    else:
        group = "中性震荡"
    return {
        "group": group,
        "as_of": report["price_date"],
        "run_id": report.get("id"),
        "metrics": {
            "absolute_20d": absolute,
            "relative_20d": short,
            "relative_60d": long,
        },
        "reason": "依据近期绝对表现与相对 SPY 表现分类；不是估值、拥挤度或基本面周期认定。",
    }


def sector_watchlist(
    rows: list[dict], report: dict | None = None, today: date | None = None
) -> list[dict]:
    today = today or datetime.now(UTC).date()
    by_id = {r["id"]: r for r in rows}
    prices = {r["ticker"]: r for r in (report or {}).get("ranking", [])}
    result = []
    for ticker, name, parent, key, confirmation, thesis, invalidation in UNIVERSE:
        row = by_id.get(key)
        evidence = None
        if row and row.get("status") == "available":
            evidence = {
                k: row[k] for k in ("name", "value", "unit", "observation_date", "url")
            }
        market = market_state(prices.get(ticker), report, today)
        result.append(
            {
                "name": name,
                "ticker": ticker,
                "parent": parent,
                "kind": "细分行业" if parent else "主要板块",
                "state": "待验证行业基本面" if evidence else "宏观数据也缺失",
                "thesis": thesis,
                "evidence": evidence,
                "confirmation": confirmation,
                "invalidation": invalidation,
                "valuation": "未接入可靠估值与盈利预期；无法判定是否低估或已充分定价",
                "bottom_status": "尚未确认筑底",
                "horizon": "6–18 个月条件观察，非买入排名",
                "market": market,
                "focus": FOCUS[market["group"]],
                "fundamental_status": "基本面阶段待验证",
            }
        )
    return result
