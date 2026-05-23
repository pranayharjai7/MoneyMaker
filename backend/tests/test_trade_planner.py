from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

from backend.trade_planner.service import construct_and_persist_trade_plan

class FakePlannerRepository:
    def __init__(self) -> None:
        self.stock = {
            "id": "nvda-uuid",
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "sector": "Technology",
        }
        self.plan_stored: dict[str, Any] | None = None
        self.targets_stored: list[dict[str, Any]] = []
        self.reasoning_stored: list[dict[str, Any]] = []
        self.recs_stored: list[dict[str, Any]] = []

    def get_stock_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        if ticker.upper() == "NVDA":
            return self.stock
        return None

    def get_price_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        return {
            "stock_id": stock_id,
            "timestamp": timestamp,
            "close": 132.40,
            "volume": 50_000_000,
        }

    def get_prices(self, stock_id: str, limit: int = 300) -> list[dict[str, Any]]:
        base = datetime(2026, 5, 20, 12, tzinfo=UTC)
        rows = [
            {
                "stock_id": stock_id,
                "timestamp": (base - timedelta(days=i)).isoformat(),
                "close": 132.40 - i * 0.5,
            }
            for i in range(150)
        ]
        return list(reversed(rows))


    def get_indicator_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        return {
            "stock_id": stock_id,
            "timestamp": timestamp,
            "rsi": 65.0,
            "sma_20": 128.50,
            "sma_50": 120.20,
            "bollinger_upper": 135.00,
            "bollinger_lower": 115.00,
            "volatility": 0.025,
            "volume_momentum": 0.18,
            "macd": 2.50,
            "macd_signal": 1.20,
        }

    def latest_signal_for_stock(self, stock_id: str) -> dict[str, Any] | None:
        return {
            "stock_id": stock_id,
            "timestamp": "2026-05-23T12:00:00Z",
            "buy_probability": 0.74,
            "sell_probability": 0.18,
            "expected_return": 0.08,
            "risk_score": 0.35,
            "suggested_hold_days": 6,
        }

    def get_signals_for_ticker(self, ticker: str, limit: int = 100) -> list[dict[str, Any]]:
        return [self.latest_signal_for_stock("nvda-uuid")]

    def get_market_regime_at_or_before(self, timestamp: str) -> dict[str, Any] | None:
        return {
            "timestamp": timestamp,
            "current_regime": "BULL TREND",
            "confidence": 0.85,
        }

    def latest_market_regime(self) -> dict[str, Any] | None:
        return self.get_market_regime_at_or_before("2026-05-23T12:00:00Z")

    def upsert_trade_plan(self, plan: dict[str, Any]) -> dict[str, Any] | None:
        self.plan_stored = {**plan, "id": "mock-plan-id", "created_at": datetime.now(tz=UTC)}
        return self.plan_stored

    def get_latest_trade_plan(self, stock_id: str) -> dict[str, Any] | None:
        return self.plan_stored

    def upsert_trade_targets(self, targets: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        self.targets_stored = list(targets)
        return self.targets_stored

    def insert_trade_reasoning(self, items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        self.reasoning_stored = list(items)
        return self.reasoning_stored

    def upsert_execution_recommendations(self, recs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        self.recs_stored = list(recs)
        return self.recs_stored

def test_construct_and_persist_trade_plan_success() -> None:
    repository = FakePlannerRepository()
    
    plan = construct_and_persist_trade_plan("NVDA", repository=repository)
    
    assert plan is not None
    assert plan["stock_id"] == "nvda-uuid"
    assert plan["current_price"] == 132.40
    assert plan["confidence"] == "HIGH"
    assert plan["regime_context"] == "BULL TREND"
    assert plan["suggested_entry_price"] == 135.67  # Breakout entry near Bollinger Upper Band
    assert plan["stop_loss"] < 135.67

    assert plan["risk_reward_ratio"] == 0.87  # Breakout ATR-adjusted risk/reward ratio

    
    # Check that children are populated
    assert len(plan["targets"]) == 3
    assert len(plan["reasoning"]) >= 3
    assert len(plan["execution_recommendations"]) == 1
    
    # Check that Fake Repository stored the data end-to-end
    assert repository.plan_stored is not None
    assert len(repository.targets_stored) == 3
    assert len(repository.reasoning_stored) >= 3
    assert len(repository.recs_stored) == 1
