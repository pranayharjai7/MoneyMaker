from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


VOLATILE_REGIMES = {"HIGH VOLATILITY", "LOW LIQUIDITY", "BEAR TREND"}


@dataclass(frozen=True)
class NotificationDecision:
    allowed: bool
    reason: str
    minimum_probability: float
    effective_daily_limit: int
    cooldown_until: str | None = None


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _regime_name(regime: Mapping[str, Any] | None) -> str:
    return str((regime or {}).get("current_regime") or "SIDEWAYS")


def minimum_probability_for_regime(
    regime: Mapping[str, Any] | None,
    settings: Settings | None = None,
) -> float:
    settings = settings or get_settings()
    if _regime_name(regime) in VOLATILE_REGIMES:
        return settings.notification_high_volatility_min_probability
    return settings.notification_default_min_probability


def _alert_probability(signal: Mapping[str, Any], alert_type: str) -> float:
    key = "buy_probability" if alert_type == "buy" else "sell_probability"
    return clamp(safe_float(signal.get(key), 0.5))


def _daily_limit(alert_type: str, settings: Settings) -> int:
    if alert_type == "buy":
        return max(0, settings.notification_max_buy_signals_per_day)
    return max(0, settings.notification_max_sell_alerts_per_day)


def _trust_adjustment(metrics: Mapping[str, Any] | None) -> tuple[float, float]:
    if not metrics:
        return 0.0, 1.0
    engagement = clamp(safe_float(metrics.get("engagement_score")))
    ignored = int(metrics.get("ignored") or 0)
    sent = max(1, int(metrics.get("notifications_sent") or 0))
    ignored_ratio = clamp(ignored / sent)
    threshold_bump = 0.0
    limit_multiplier = 1.0
    if sent >= 10 and engagement < 0.25:
        threshold_bump += 0.07
        limit_multiplier = 0.4
    elif sent >= 5 and engagement < 0.45:
        threshold_bump += 0.04
        limit_multiplier = 0.7
    if ignored_ratio > 0.6:
        threshold_bump += 0.03
        limit_multiplier = min(limit_multiplier, 0.5)
    return threshold_bump, limit_multiplier


def should_send_notification(
    repository: SupabaseRepository,
    user_id: str,
    signal: Mapping[str, Any],
    alert_type: str,
    regime: Mapping[str, Any] | None = None,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> NotificationDecision:
    settings = settings or get_settings()
    now = (now or datetime.now(tz=UTC)).astimezone(UTC)
    metrics = repository.get_notification_metrics(user_id)
    threshold_bump, limit_multiplier = _trust_adjustment(metrics)
    minimum_probability = clamp(minimum_probability_for_regime(regime, settings) + threshold_bump)

    if _alert_probability(signal, alert_type) < minimum_probability:
        return NotificationDecision(
            allowed=False,
            reason="below_adaptive_probability_threshold",
            minimum_probability=minimum_probability,
            effective_daily_limit=max(1, int(_daily_limit(alert_type, settings) * limit_multiplier)),
        )

    effective_daily_limit = max(1, int(_daily_limit(alert_type, settings) * limit_multiplier))
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    alerts_today = repository.count_alerts_for_user_since(user_id, alert_type, _iso(day_start))
    if alerts_today >= effective_daily_limit:
        return NotificationDecision(
            allowed=False,
            reason="daily_limit_reached",
            minimum_probability=minimum_probability,
            effective_daily_limit=effective_daily_limit,
        )

    stock_id = str(signal.get("stock_id") or "")
    latest = repository.latest_alert_for_user_stock(user_id, stock_id) if stock_id else None
    if latest and latest.get("created_at"):
        cooldown_until = _to_utc_datetime(latest["created_at"]) + timedelta(
            hours=max(0, settings.notification_cooldown_hours_per_stock)
        )
        if now < cooldown_until:
            return NotificationDecision(
                allowed=False,
                reason="stock_cooldown_active",
                minimum_probability=minimum_probability,
                effective_daily_limit=effective_daily_limit,
                cooldown_until=_iso(cooldown_until),
            )

    return NotificationDecision(
        allowed=True,
        reason="allowed",
        minimum_probability=minimum_probability,
        effective_daily_limit=effective_daily_limit,
    )


def record_notification_sent(
    repository: SupabaseRepository,
    user_id: str,
    count: int = 1,
) -> dict[str, Any] | None:
    return repository.increment_notification_metrics(user_id, sent=count)


def record_notification_engagement(
    repository: SupabaseRepository,
    user_id: str,
    opened: int = 0,
    ignored: int = 0,
) -> dict[str, Any] | None:
    return repository.increment_notification_metrics(user_id, opened=opened, ignored=ignored)


def build_notification_engagement_report(
    repository: SupabaseRepository | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    metrics = repository.list_notification_metrics(limit=limit)
    sent = sum(int(row.get("notifications_sent") or 0) for row in metrics)
    opened = sum(int(row.get("opened") or 0) for row in metrics)
    ignored = sum(int(row.get("ignored") or 0) for row in metrics)
    engagement_score = clamp(opened / sent) if sent else 0.0
    return {
        "summary": {
            "users_tracked": len(metrics),
            "notifications_sent": sent,
            "opened": opened,
            "ignored": ignored,
            "engagement_score": engagement_score,
        },
        "users": metrics,
    }
