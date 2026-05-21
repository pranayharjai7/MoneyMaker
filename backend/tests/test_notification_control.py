from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.config import Settings
from backend.notification_control.service import (
    minimum_probability_for_regime,
    should_send_notification,
)


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.metrics: dict[str, dict[str, Any]] = {}
        self.alerts_today = 0
        self.latest_alert: dict[str, Any] | None = None

    def get_notification_metrics(self, user_id: str) -> dict[str, Any] | None:
        return self.metrics.get(user_id)

    def count_alerts_for_user_since(
        self,
        user_id: str,
        alert_type: str,
        since_timestamp: str,
    ) -> int:
        del user_id, alert_type, since_timestamp
        return self.alerts_today

    def latest_alert_for_user_stock(self, user_id: str, stock_id: str) -> dict[str, Any] | None:
        del user_id, stock_id
        return self.latest_alert


def test_high_volatility_increases_notification_threshold() -> None:
    settings = Settings(
        notification_default_min_probability=0.62,
        notification_high_volatility_min_probability=0.72,
    )

    assert (
        minimum_probability_for_regime({"current_regime": "HIGH VOLATILITY"}, settings)
        == 0.72
    )


def test_notification_throttling_respects_limits_and_cooldown() -> None:
    repository = FakeNotificationRepository()
    settings = Settings(
        notification_max_buy_signals_per_day=1,
        notification_cooldown_hours_per_stock=12,
        notification_default_min_probability=0.62,
    )
    signal = {"stock_id": "stock-1", "buy_probability": 0.8}

    allowed = should_send_notification(
        repository=repository,
        user_id="user-1",
        signal=signal,
        alert_type="buy",
        settings=settings,
        now=datetime(2026, 5, 21, 10, tzinfo=UTC),
    )
    assert allowed.allowed

    repository.alerts_today = 1
    limited = should_send_notification(
        repository=repository,
        user_id="user-1",
        signal=signal,
        alert_type="buy",
        settings=settings,
        now=datetime(2026, 5, 21, 11, tzinfo=UTC),
    )
    assert not limited.allowed
    assert limited.reason == "daily_limit_reached"

    repository.alerts_today = 0
    repository.latest_alert = {
        "created_at": (datetime(2026, 5, 21, 10, tzinfo=UTC) - timedelta(hours=1)).isoformat()
    }
    cooled = should_send_notification(
        repository=repository,
        user_id="user-1",
        signal=signal,
        alert_type="buy",
        settings=settings,
        now=datetime(2026, 5, 21, 10, tzinfo=UTC),
    )
    assert not cooled.allowed
    assert cooled.reason == "stock_cooldown_active"


def test_low_trust_user_gets_stricter_threshold() -> None:
    repository = FakeNotificationRepository()
    repository.metrics["user-1"] = {
        "notifications_sent": 20,
        "opened": 2,
        "ignored": 15,
        "engagement_score": 0.1,
    }
    signal = {"stock_id": "stock-1", "buy_probability": 0.65}

    decision = should_send_notification(
        repository=repository,
        user_id="user-1",
        signal=signal,
        alert_type="buy",
        settings=Settings(notification_default_min_probability=0.62),
        now=datetime(2026, 5, 21, 10, tzinfo=UTC),
    )

    assert not decision.allowed
    assert decision.minimum_probability > 0.65
