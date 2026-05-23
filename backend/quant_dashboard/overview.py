from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.calibration_intelligence.service import build_calibration_intelligence_payload
from backend.db.repository import SupabaseRepository
from backend.drift_visualization.service import build_drift_visualization_payload
from backend.infra_observability.service import build_infra_observability_payload
from backend.model_intelligence.service import build_model_intelligence_payload
from backend.regime_analytics.service import build_regime_analytics_payload
from backend.signal_monitoring.service import build_signal_monitoring_payload


def build_overview_payload(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    signals = build_signal_monitoring_payload(repository)
    models = build_model_intelligence_payload(repository)
    calibration = build_calibration_intelligence_payload(repository)
    regimes = build_regime_analytics_payload(repository)
    drift = build_drift_visualization_payload(repository)
    infra = build_infra_observability_payload(repository)

    return {
        "kpis": {
            "active_signals": signals["summary"]["active_signals"],
            "current_regime": regimes["current"]["regime"],
            "models_tracked": len(models.get("leaderboard") or []),
            "calibration_error": calibration.get("aggregate_calibration_error"),
            "drift_warnings": len(drift.get("warnings") or []),
            "system_status": infra["health_cards"][0]["status"],
        },
        "signals": signals,
        "models": models,
        "calibration": calibration,
        "regimes": regimes,
        "drift": drift,
        "infra": infra,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
