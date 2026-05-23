from __future__ import annotations

from dataclasses import dataclass

from backend.data_pipeline.providers import StockRecord


REQUIRED_ETFS: tuple[str, ...] = ("SPY", "QQQ", "IWM", "XLF", "XLK")

# S&P 100 large-cap constituents (US equities). ETFs listed separately.
SP100_TICKERS: tuple[str, ...] = (
    "AAPL",
    "ABBV",
    "ABT",
    "ACN",
    "ADBE",
    "AIG",
    "AMD",
    "AMGN",
    "AMT",
    "AMZN",
    "AVGO",
    "AXP",
    "BA",
    "BAC",
    "BK",
    "BKNG",
    "BLK",
    "BMY",
    "BRK.B",
    "C",
    "CAT",
    "CL",
    "CMCSA",
    "COF",
    "COP",
    "COST",
    "CRM",
    "CSCO",
    "CVS",
    "CVX",
    "DE",
    "DHR",
    "DIS",
    "DUK",
    "EMR",
    "EXC",
    "FDX",
    "GE",
    "GILD",
    "GM",
    "GOOG",
    "GOOGL",
    "GS",
    "HD",
    "HON",
    "IBM",
    "INTC",
    "INTU",
    "ISRG",
    "JNJ",
    "JPM",
    "KO",
    "LIN",
    "LLY",
    "LMT",
    "LOW",
    "MA",
    "MCD",
    "MDLZ",
    "MDT",
    "MET",
    "META",
    "MMM",
    "MO",
    "MRK",
    "MS",
    "MSFT",
    "NEE",
    "NFLX",
    "NKE",
    "NVDA",
    "ORCL",
    "PEP",
    "PFE",
    "PG",
    "PM",
    "QCOM",
    "RTX",
    "SBUX",
    "SCHW",
    "SO",
    "SPG",
    "T",
    "TGT",
    "TMO",
    "TMUS",
    "TSLA",
    "TXN",
    "UNH",
    "UNP",
    "UPS",
    "USB",
    "V",
    "VZ",
    "WFC",
    "WMT",
    "XOM",
)

SECTOR_LEADER_ETFS: tuple[str, ...] = (
    "SPY",
    "QQQ",
    "IWM",
    "XLF",
    "XLK",
    "XLE",
    "XLV",
    "XLI",
    "XLY",
    "XLP",
    "XLU",
    "XLB",
    "XLRE",
    "DIA",
    "VTI",
)

TECH_FOCUS_TICKERS: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "GOOG",
    "META",
    "AMZN",
    "AVGO",
    "AMD",
    "INTC",
    "QCOM",
    "CRM",
    "ADBE",
    "ORCL",
    "NOW",
    "PANW",
    "SNOW",
    "PLTR",
    "MU",
    "TXN",
    "IBM",
    "CSCO",
    "INTU",
    "NFLX",
    "TSLA",
    "QQQ",
    "XLK",
    "SMH",
    "SOXX",
)

HIGH_LIQUIDITY_TICKERS: tuple[str, ...] = tuple(
    dict.fromkeys(
        [
            *REQUIRED_ETFS,
            *SECTOR_LEADER_ETFS,
            "AAPL",
            "MSFT",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "TSLA",
            "JPM",
            "V",
            "UNH",
            "XOM",
            "BAC",
            "WMT",
            "LLY",
            "AVGO",
            "MA",
            "COST",
            "HD",
            "PG",
            "JNJ",
            "BRK.B",
        ]
    )
)


@dataclass(frozen=True)
class UniverseDefinition:
    slug: str
    description: str
    tickers: tuple[str, ...]

    def stock_records(self) -> list[StockRecord]:
        return [
            StockRecord(ticker=ticker, company_name=ticker, exchange="US")
            for ticker in self.tickers
        ]


UNIVERSE_DEFINITIONS: dict[str, UniverseDefinition] = {
    "core_large_cap": UniverseDefinition(
        slug="core_large_cap",
        description=(
            "S&P 100 large caps, required benchmark ETFs (SPY, QQQ, IWM, XLF, XLK), "
            "and sector leader ETFs for historical intelligence backfill."
        ),
        tickers=tuple(
            dict.fromkeys([*SP100_TICKERS, *SECTOR_LEADER_ETFS, *REQUIRED_ETFS])
        ),
    ),
    "tech_focus": UniverseDefinition(
        slug="tech_focus",
        description="Technology and growth leaders plus QQQ, XLK, and semiconductor ETFs.",
        tickers=TECH_FOCUS_TICKERS,
    ),
    "etf_only": UniverseDefinition(
        slug="etf_only",
        description="Liquid benchmark and sector ETFs only (no single stocks).",
        tickers=tuple(dict.fromkeys([*REQUIRED_ETFS, *SECTOR_LEADER_ETFS])),
    ),
    "high_liquidity": UniverseDefinition(
        slug="high_liquidity",
        description="Most liquid US names and ETFs for fast replay and calibration bootstrap.",
        tickers=HIGH_LIQUIDITY_TICKERS,
    ),
}


def get_universe_definition(slug: str) -> UniverseDefinition:
    normalized = slug.strip().lower()
    if normalized not in UNIVERSE_DEFINITIONS:
        known = ", ".join(sorted(UNIVERSE_DEFINITIONS))
        raise KeyError(f"Unknown universe '{slug}'. Known universes: {known}")
    return UNIVERSE_DEFINITIONS[normalized]


def list_universe_slugs() -> list[str]:
    return sorted(UNIVERSE_DEFINITIONS)
