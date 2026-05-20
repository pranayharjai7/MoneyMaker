from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.regime.service import detect_market_regime, refresh_market_regime


def _price_rows(stock_id: str, start: float, drift: float, days: int = 80) -> list[dict[str, Any]]:
    base = datetime(2026, 1, 1, 21, tzinfo=UTC)
    rows = []
    price = start
    for index in range(days):
        price *= 1.0 + drift
        rows.append(
            {
                "stock_id": stock_id,
                "timestamp": (base + timedelta(days=index)).isoformat(),
                "close": price,
                "volume": 1_000_000 + index * 1_000,
            }
        )
    return rows


class FakeRegimeRepository:
    def __init__(self) -> None:
        self.stored: dict[str, Any] | None = None
        self.stocks = [
            {"id": "spx", "ticker": "SPX", "sector": "Index"},
            {"id": "a", "ticker": "AAA", "sector": "Technology"},
            {"id": "b", "ticker": "BBB", "sector": "Technology"},
        ]
        self.prices_by_id = {
            "spx": _price_rows("spx", 100.0, 0.003),
            "a": _price_rows("a", 50.0, 0.002),
            "b": _price_rows("b", 70.0, 0.0015),
        }

    def get_stock_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        for stock in self.stocks:
            if stock["ticker"] == ticker:
                return stock
        return None

    def get_prices_for_ticker(self, ticker: str, limit: int = 300) -> list[dict[str, Any]]:
        stock = self.get_stock_by_ticker(ticker)
        if not stock:
            return []
        return self.get_prices(stock["id"], limit=limit)

    def list_stocks(self) -> list[dict[str, Any]]:
        return self.stocks

    def get_prices(self, stock_id: str, limit: int = 300) -> list[dict[str, Any]]:
        return self.prices_by_id.get(stock_id, [])[-limit:]

    def upsert_market_regime(self, row: dict[str, Any]) -> dict[str, Any]:
        self.stored = row
        return row


def test_detect_market_regime_identifies_bull_trend() -> None:
    regime = detect_market_regime(repository=FakeRegimeRepository())

    assert regime["current_regime"] == "BULL TREND"
    assert regime["confidence"] > 0.7
    assert regime["feature_payload"]["reference_ticker"] == "SPX"


def test_refresh_market_regime_persists_snapshot() -> None:
    repository = FakeRegimeRepository()

    regime = refresh_market_regime(repository=repository)

    assert repository.stored == regime
    assert regime["current_regime"] == "BULL TREND"
