from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository
from backend.notification_control.service import (
    record_notification_sent,
    should_send_notification,
)


def should_generate_buy_alert(signal: Mapping[str, Any], settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return (
        safe_float(signal.get("buy_probability")) > settings.alert_min_buy_probability
        and safe_float(signal.get("expected_return")) > settings.alert_min_expected_return
        and safe_float(signal.get("risk_score"), 1.0) < settings.alert_max_risk_score
    )


def should_generate_sell_alert(signal: Mapping[str, Any], settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return (
        safe_float(signal.get("sell_probability")) > settings.alert_min_buy_probability
        and safe_float(signal.get("expected_return")) < -settings.alert_min_expected_return
        and safe_float(signal.get("risk_score"), 1.0) < settings.alert_max_risk_score
    )


def _alert_row(user_id: str, signal: Mapping[str, Any], alert_type: str) -> dict[str, Any]:
    probability_key = "buy_probability" if alert_type == "buy" else "sell_probability"
    return {
        "user_id": user_id,
        "stock_id": signal["stock_id"],
        "alert_type": alert_type,
        "probability": safe_float(signal.get(probability_key)),
        "expected_return": safe_float(signal.get("expected_return")),
        "risk_score": safe_float(signal.get("risk_score"), 1.0),
        "source_signal_timestamp": signal.get("timestamp"),
        "is_read": False,
    }


def generate_alerts(
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
    stock_ids: Iterable[str] | None = None,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    settings = settings or get_settings()
    if stock_ids is None:
        stock_ids = [stock["id"] for stock in repository.list_stocks()]

    alert_rows: list[dict[str, Any]] = []
    latest_regime = repository.latest_market_regime()
    for stock_id in stock_ids:
        signal = repository.latest_signal_for_stock(stock_id)
        if not signal:
            continue
        if should_generate_buy_alert(signal, settings):
            alert_type = "buy"
        elif should_generate_sell_alert(signal, settings):
            alert_type = "sell"
        else:
            continue

        for user_id in repository.users_interested_in_stock(stock_id):
            decision = should_send_notification(
                repository=repository,
                user_id=user_id,
                signal=signal,
                alert_type=alert_type,
                regime=latest_regime,
                settings=settings,
            )
            if decision.allowed:
                alert_rows.append(_alert_row(user_id, signal, alert_type))

    stored = repository.create_alerts(alert_rows)
    sent_by_user: dict[str, int] = {}
    for row in stored:
        user_id = str(row.get("user_id") or "")
        if user_id:
            sent_by_user[user_id] = sent_by_user.get(user_id, 0) + 1
    for user_id, count in sent_by_user.items():
        record_notification_sent(repository, user_id, count=count)
    return {"alerts": len(stored)}
