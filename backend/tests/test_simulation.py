from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.simulation.engine import run_paper_trading_simulation


class FakeSimulationRepository:
    def __init__(self) -> None:
        base = datetime(2026, 5, 1, 21, tzinfo=UTC)
        self.signals = [
            {
                "stock_id": "stock-1",
                "timestamp": base.isoformat(),
                "buy_probability": 0.74,
                "sell_probability": 0.26,
                "risk_score": 0.25,
                "signal_type": "buy",
                "suggested_hold_days": 3,
            },
            {
                "stock_id": "stock-1",
                "timestamp": (base + timedelta(days=5)).isoformat(),
                "buy_probability": 0.30,
                "sell_probability": 0.70,
                "risk_score": 0.30,
                "signal_type": "sell",
                "suggested_hold_days": 2,
            },
        ]
        self.prices = []
        price = 100.0
        for index in range(12):
            price += 1.0 if index < 6 else -1.5
            self.prices.append(
                {
                    "stock_id": "stock-1",
                    "timestamp": (base + timedelta(days=index)).isoformat(),
                    "close": price,
                }
            )
        self.result: dict[str, Any] | None = None

    def list_signals_for_backtest(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.signals[:limit]

    def get_price_at_or_after(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.prices
            if row["stock_id"] == stock_id and row["timestamp"] >= timestamp
        ]
        return rows[0] if rows else None

    def insert_backtest_result(self, row: dict[str, Any]) -> dict[str, Any]:
        self.result = row
        return row


def test_run_paper_trading_simulation_tracks_performance_metrics() -> None:
    repository = FakeSimulationRepository()

    result = run_paper_trading_simulation(repository=repository)

    assert repository.result == result
    assert result["trade_count"] == 2
    assert result["strategy_return"] != 0
    assert result["max_drawdown"] <= 0
    assert "trades" in result["result_payload"]
