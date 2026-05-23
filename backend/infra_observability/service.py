from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.db.repository import SupabaseRepository
from backend.observability.metrics import metrics_registry
from backend.observability.service import (
    models_health,
    notifications_health,
    realtime_health,
    system_health,
)


def build_infra_observability_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    system = system_health(repository=repository)
    models = models_health(repository=repository)
    realtime = realtime_health(repository=repository)
    notifications = notifications_health(repository=repository)
    metrics = metrics_registry.snapshot()

    health_cards = [
        {"component": "API", "status": _normalize_status(system.get("status")), "details": system},
        {"component": "Realtime", "status": _normalize_status(realtime.get("status")), "details": realtime},
        {"component": "Models", "status": _normalize_status(models.get("status")), "details": models},
        {
            "component": "Notifications",
            "status": _normalize_status(notifications.get("status")),
            "details": notifications,
        },
        {
            "component": "Supabase",
            "status": _normalize_status((system.get("components") or {}).get("supabase", {}).get("status")),
            "details": (system.get("components") or {}).get("supabase"),
        },
    ]

    stored = repository.list_infra_metrics(limit=200)
    return {
        "health_cards": health_cards,
        "metrics": metrics,
        "stored_metrics": stored,
        "queue": {
            "pending_notifications": notifications.get("pending", 0),
            "failed_notifications": notifications.get("failed_recent", 0),
        },
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def _normalize_status(status: Any) -> str:
    value = str(status or "ok").lower()
    if value in {"ok", "configured", "warming_up"}:
        return "HEALTHY"
    if value in {"degraded", "missing"}:
        return "DEGRADED"
    return "CRITICAL"
