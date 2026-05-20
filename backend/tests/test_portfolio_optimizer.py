from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.portfolio.optimizer import optimize_portfolio_weights


def _prices(stock_id: str, drift: float) -> list[dict[str, Any]]:
    base = datetime(2026, 1, 1, 21, tzinfo=UTC)
    price = 100.0
    rows = []
    for index in range(90):
        price *= 1.0 + drift + (0.001 if index % 2 == 0 else -0.001)
        rows.append(
            {
                "stock_id": stock_id,
                "timestamp": (base + timedelta(days=index)).isoformat(),
                "close": price,
            }
        )
    return rows


class FakePortfolioRepository:
    def __init__(self) -> None:
        timestamp = "2026-05-20T21:00:00+00:00"
        stocks = {
            "nvda": {"ticker": "NVDA", "sector": "Technology", "company_name": "NVIDIA"},
            "amd": {"ticker": "AMD", "sector": "Technology", "company_name": "AMD"},
            "msft": {"ticker": "MSFT", "sector": "Technology", "company_name": "Microsoft"},
            "jpm": {"ticker": "JPM", "sector": "Financials", "company_name": "JPMorgan"},
        }
        self.signals = [
            {
                "stock_id": stock_id,
                "timestamp": timestamp,
                "buy_probability": 0.72,
                "sell_probability": 0.28,
                "expected_return": 0.05,
                "risk_score": 0.35,
                "stocks": stock,
            }
            for stock_id, stock in stocks.items()
        ]
        self.prices = {
            "nvda": _prices("nvda", 0.003),
            "amd": _prices("amd", 0.003),
            "msft": _prices("msft", 0.001),
            "jpm": _prices("jpm", 0.0008),
        }
        self.rows: list[dict[str, Any]] = []

    def list_signals(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.signals[:limit]

    def get_indicator_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any]:
        return {"volatility": 0.02}

    def get_prices(self, stock_id: str, limit: int = 300) -> list[dict[str, Any]]:
        return self.prices[stock_id][-limit:]

    def insert_portfolio_allocations(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.rows = rows
        return rows


def test_optimize_portfolio_weights_caps_semiconductor_and_single_name_exposure() -> None:
    repository = FakePortfolioRepository()

    result = optimize_portfolio_weights(repository=repository)

    semiconductor_total = sum(
        row["allocation"] for row in repository.rows if row["ticker"] in {"NVDA", "AMD"}
    )
    assert result["portfolio_weights"] == 4
    assert max(row["allocation"] for row in repository.rows) <= 0.12
    assert semiconductor_total <= 0.20
