from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository
from backend.drift_detection.service import build_drift_report, detect_model_drift


def build_drift_visualization_payload(
    repository: SupabaseRepository | None = None,
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    if refresh:
        detect_model_drift(repository=repository)

    report = build_drift_report(repository=repository, limit=500)
    stored = repository.list_drift_visualizations(limit=500)
    events = report.get("events") or []

    timeline = [
        {
            "model_name": event.get("model_name"),
            "drift_score": safe_float(event.get("drift_score")),
            "severity": event.get("severity"),
            "created_at": event.get("created_at"),
        }
        for event in sorted(events, key=lambda row: str(row.get("created_at")))
    ]

    warnings = _automatic_warnings(events, repository)
    feature_heatmap = _feature_heatmap(stored, events)

    return {
        "timeline": timeline,
        "stored_visualizations": stored,
        "feature_drift_heatmap": feature_heatmap,
        "warnings": warnings,
        "active_model_weight_multipliers": report.get("active_model_weight_multipliers"),
        "disabled_models": report.get("disabled_models"),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def _automatic_warnings(
    events: list[dict[str, Any]],
    repository: SupabaseRepository,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    performances = {row["model_name"]: row for row in repository.list_model_performance()}

    for event in events:
        model_name = str(event.get("model_name"))
        severity = str(event.get("severity"))
        drift_score = safe_float(event.get("drift_score"))
        if severity in {"high", "critical"}:
            warnings.append(
                {
                    "level": severity,
                    "message": f"{model_name} drift rising (score {drift_score:.2f})",
                    "model_name": model_name,
                }
            )

    for performance in performances.values():
        calibration_error = safe_float(performance.get("calibration_error"))
        if calibration_error >= 0.18:
            warnings.append(
                {
                    "level": "medium",
                    "message": f"{performance['model_name']} calibration degrading",
                    "model_name": performance["model_name"],
                }
            )
    return warnings


def _feature_heatmap(
    stored: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for event in events[-20:]:
        metadata = event.get("metadata") or {}
        components = metadata.get("components") if isinstance(metadata, dict) else {}
        if not isinstance(components, dict):
            components = {}
        for feature, score in components.items():
            rows.append(
                {
                    "model_name": event.get("model_name"),
                    "feature": feature,
                    "drift": safe_float(score),
                }
            )
    if rows:
        return rows
    for row in stored[:20]:
        feature_drift = row.get("feature_drift") or {}
        if isinstance(feature_drift, dict):
            for feature, score in feature_drift.items():
                rows.append(
                    {
                        "model_name": row.get("model_name"),
                        "feature": feature,
                        "drift": safe_float(score),
                    }
                )
    return rows
