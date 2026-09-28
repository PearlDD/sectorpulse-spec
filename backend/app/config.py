"""Project-wide constants and configuration for SectorPulse."""

from datetime import date


# ---------------------------------------------------------------------------
# Sector ETFs — 11 SPDR Select Sector ETFs + SPY benchmark
# ---------------------------------------------------------------------------
SECTOR_TICKERS: list[str] = [
    "XLB",  # Materials
    "XLC",  # Communication Services
    "XLE",  # Energy
    "XLF",  # Financials
    "XLI",  # Industrials
    "XLK",  # Technology
    "XLP",  # Consumer Staples
    "XLRE",  # Real Estate
    "XLU",  # Utilities
    "XLV",  # Health Care
    "XLY",  # Consumer Discretionary
]

BENCHMARK_TICKER: str = "SPY"

# Launch dates for newer sector ETFs — all others available from 1998-12-16
SECTOR_LAUNCH_DATES: dict[str, date] = {
    "XLB": date(1998, 12, 16),
    "XLE": date(1998, 12, 16),
    "XLF": date(1998, 12, 16),
    "XLI": date(1998, 12, 16),
    "XLK": date(1998, 12, 16),
    "XLP": date(1998, 12, 16),
    "XLU": date(1998, 12, 16),
    "XLV": date(1998, 12, 16),
    "XLY": date(1998, 12, 16),
    "XLRE": date(2015, 10, 7),
    "XLC": date(2018, 6, 18),
}


def get_available_sectors(as_of: date) -> list[str]:
    """Return sector tickers that were tradeable on *as_of* date.

    Sectors are included only if their launch date is on or before *as_of*.
    The returned list is sorted alphabetically for deterministic ordering.
    """
    return sorted(
        ticker
        for ticker, launch in SECTOR_LAUNCH_DATES.items()
        if launch <= as_of
    )


# ---------------------------------------------------------------------------
# FRED macro indicator series IDs
# ---------------------------------------------------------------------------
FRED_SERIES: dict[str, str] = {
    "ISM_PMI": "MANEMP",       # ISM Manufacturing PMI (proxy via manufacturing employment)
    "YIELD_CURVE": "T10Y2Y",   # 10-Year minus 2-Year Treasury spread
    "INITIAL_CLAIMS": "ICSA",  # Initial jobless claims
    "LEI": "USALOLITONOSTSAM",  # Leading Economic Index (OECD CLI proxy)
    "UNEMPLOYMENT": "UNRATE",  # Unemployment rate
    "CPI": "CPIAUCSL",        # CPI for All Urban Consumers
}

# V2 additional series — credit spreads and VIX proxy
FRED_SERIES_V2: dict[str, str] = {
    "HY_SPREAD": "BAMLH0A0HYM2",   # ICE BofA US High Yield OAS
    "IG_SPREAD": "BAMLC0A0CM",      # ICE BofA US Corporate OAS
    "VIX": "VIXCLS",               # CBOE VIX
}


# ---------------------------------------------------------------------------
# Business cycle → sector mapping
# ---------------------------------------------------------------------------
CYCLE_PHASES = ["recovery", "expansion", "slowdown", "contraction"]

CYCLE_SECTOR_MAP: dict[str, list[str]] = {
    "recovery": ["XLF", "XLY", "XLI", "XLRE", "XLB"],
    "expansion": ["XLK", "XLY", "XLI", "XLC", "XLE"],
    "slowdown": ["XLE", "XLV", "XLP", "XLU", "XLB"],
    "contraction": ["XLV", "XLP", "XLU", "XLK", "XLRE"],
}
