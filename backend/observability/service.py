from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.config import Settings, get_settings
from backend.db.repository import SupabaseRepository
from backend.observability.metrics import metrics_registry


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def system_health(
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    settings = settings or get_settings()
    components: dict[str, Any] = {}
    try:
        repository.list_stocks()
        components["supabase"] = {"status": "ok"}
    except Exception as exc:
        components["supabase"] = {"status": "degraded", "error": str(exc)}

    components["redis"] = {"status": "configured" if settings.redis_url else "missing"}
    metrics = metrics_registry.snapshot()
    return {
        "status": "ok"
        if all(component.get("status") in {"ok", "configured"} for component in components.values())
        else "degraded",
        "components": components,
        "metrics": metrics,
    }


def models_health(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    performances = repository.list_model_performance()
    since = datetime.now(tz=UTC) - timedelta(days=14)
    drift_events = repository.list_recent_model_drift_events(since_timestamp=_iso(since), limit=100)
    critical = [event for event in drift_events if event.get("severity") == "critical"]
    return {
        "status": "degraded" if critical else "ok",
        "models_tracked": len(performances),
        "recent_drift_events": len(drift_events),
        "critical_models": sorted({str(event["model_name"]) for event in critical if event.get("model_name")}),
        "performance": performances,
    }


def realtime_health(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    signals = repository.list_signals(limit=1)
    notification_events = repository.list_recent_notification_events(limit=1)
    return {
        "status": "ok" if signals else "warming_up",
        "latest_signal_at": signals[0].get("timestamp") if signals else None,
        "latest_notification_event_at": notification_events[0].get("created_at")
        if notification_events
        else None,
    }


def notifications_health(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    pending = repository.list_recent_notification_events(status="pending", limit=100)
    failed = repository.list_recent_notification_events(status="failed", limit=100)
    sent = repository.list_recent_notification_events(status="sent", limit=100)
    total_delivery = len(sent) + len(failed)
    success_rate = len(sent) / total_delivery if total_delivery else 1.0
    metrics_registry.observe("notification_delivery_success", success_rate)
    return {
        "status": "degraded" if len(failed) > len(sent) and failed else "ok",
        "pending": len(pending),
        "failed_recent": len(failed),
        "sent_recent": len(sent),
        "delivery_success_rate": success_rate,
    }
