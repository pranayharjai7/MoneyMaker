from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.notification_control.service import build_notification_engagement_report


def build_notification_analytics_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    engagement = build_notification_engagement_report(repository=repository)
    stored = repository.list_notification_engagement(limit=200)
    events = repository.list_recent_notification_events(limit=500)

    summary = engagement.get("summary") or {}
    sent = int(summary.get("notifications_sent") or 0)
    opened = int(summary.get("opened") or 0)
    ignored = int(summary.get("ignored") or 0)
    viewed = max(opened - ignored, 0)
    acted = int(round(opened * clamp(safe_float(summary.get("engagement_score")))))

    funnel = [
        {"stage": "Sent", "count": sent},
        {"stage": "Opened", "count": opened},
        {"stage": "Viewed", "count": viewed},
        {"stage": "Acted upon", "count": acted},
    ]

    fatigue_score = clamp(ignored / sent) if sent else 0.0

    return {
        "summary": summary,
        "funnel": funnel,
        "fatigue_score": round(fatigue_score, 4),
        "period_engagement": stored,
        "recent_events": events[:100],
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
