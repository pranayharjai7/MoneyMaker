from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


RECENT_WINDOW_DAYS = 30
BASELINE_WINDOW_DAYS = 90
DRIFT_EVENT_LOOKBACK_DAYS = 14


@dataclass(frozen=True)
class DriftAssessment:
    model_name: str
    drift_score: float
    drift_type: str
    severity: str
    recommended_action: str
    components: dict[str, float]

    def to_row(self, created_at: datetime) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "drift_score": self.drift_score,
            "drift_type": self.drift_type,
            "severity": self.severity,
            "metadata": {
                "recommended_action": self.recommended_action,
                "components": self.components,
            },
            "created_at": _iso(created_at),
        }


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


def _severity(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _recommended_action(severity: str) -> str:
    if severity == "critical":
        return "disable_unstable_model_and_trigger_retraining"
    if severity == "high":
        return "reduce_ensemble_weight_and_trigger_retraining"
    if severity == "medium":
        return "reduce_ensemble_weight"
    return "monitor"


def _component_type(components: Mapping[str, float]) -> str:
    if not components:
        return "unknown"
    return max(components.items(), key=lambda item: item[1])[0]


def _group_by_model(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        model_name = row.get("model_name")
        if model_name:
            grouped[str(model_name)].append(row)
    return grouped


def _accuracy(rows: Sequence[Mapping[str, Any]]) -> float:
    if not rows:
        return 0.0
    return clamp(sum(1 for row in rows if bool(row.get("success"))) / len(rows))


def _prediction_instability(
    model_name: str,
    predictions_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
) -> float:
    probabilities = [
        clamp(safe_float(row.get("probability_up"), 0.5))
        for row in predictions_by_model.get(model_name, [])
    ]
    if len(probabilities) < 3:
        return 0.0
    return pstdev(probabilities)


def _feature_drift_score(rows: Sequence[Mapping[str, Any]]) -> float:
    if len(rows) < 40:
        return 0.0
    ordered = sorted(rows, key=lambda row: str(row.get("timestamp") or ""))
    split = max(1, int(len(ordered) * 0.7))
    baseline = ordered[:split]
    recent = ordered[split:]
    scores = []
    for key in ("volatility", "volume_momentum", "rsi", "macd"):
        baseline_values = [safe_float(row.get(key)) for row in baseline if row.get(key) is not None]
        recent_values = [safe_float(row.get(key)) for row in recent if row.get(key) is not None]
        if len(baseline_values) < 5 or len(recent_values) < 5:
            continue
        baseline_std = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
        denominator = max(baseline_std, 0.01)
        scores.append(abs(fmean(recent_values) - fmean(baseline_values)) / denominator)
    if not scores:
        return 0.0
    return clamp(fmean(scores) / 3.0)


def _accuracy_degradation(
    model_name: str,
    recent_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    baseline_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    settings: Settings,
) -> float:
    recent_rows = recent_by_model.get(model_name, [])
    baseline_rows = baseline_by_model.get(model_name, [])
    recent_accuracy = _accuracy(recent_rows)
    baseline_accuracy = _accuracy(baseline_rows)
    if baseline_rows and recent_rows and recent_accuracy < baseline_accuracy:
        return clamp((baseline_accuracy - recent_accuracy) / max(baseline_accuracy, 0.01))
    if recent_rows and recent_accuracy < settings.drift_min_accuracy:
        return clamp((settings.drift_min_accuracy - recent_accuracy) / max(settings.drift_min_accuracy, 0.01))
    return 0.0


def assess_model_drift(
    model_performance: Mapping[str, Any],
    recent_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    baseline_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    predictions_by_model: Mapping[str, Sequence[Mapping[str, Any]]],
    feature_drift: float,
    settings: Settings | None = None,
) -> DriftAssessment | None:
    settings = settings or get_settings()
    model_name = str(model_performance.get("model_name") or "")
    if not model_name:
        return None

    sharpe = safe_float(model_performance.get("sharpe_contribution"))
    calibration_error = safe_float(model_performance.get("calibration_error"))
    instability = _prediction_instability(model_name, predictions_by_model)
    components = {
        "rolling_accuracy_degradation": _accuracy_degradation(
            model_name,
            recent_by_model,
            baseline_by_model,
            settings,
        ),
        "calibration_decay": clamp(
            (calibration_error - settings.drift_max_calibration_error)
            / max(settings.drift_max_calibration_error, 0.01)
        ),
        "prediction_instability": clamp(
            (instability - settings.drift_prediction_instability_threshold)
            / max(settings.drift_prediction_instability_threshold, 0.01)
        ),
        "feature_drift": feature_drift,
        "sharpe_deterioration": clamp(
            (settings.drift_min_sharpe_ratio - sharpe)
            / max(abs(settings.drift_min_sharpe_ratio), 0.01)
        ),
    }
    drift_score = clamp(max(components.values()))
    if drift_score <= 0:
        return None
    severity = _severity(drift_score)
    return DriftAssessment(
        model_name=model_name,
        drift_score=drift_score,
        drift_type=_component_type(components),
        severity=severity,
        recommended_action=_recommended_action(severity),
        components={key: round(value, 6) for key, value in components.items()},
    )


def detect_model_drift(
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    settings = settings or get_settings()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)

    recent_start = as_of - timedelta(days=RECENT_WINDOW_DAYS)
    baseline_start = as_of - timedelta(days=RECENT_WINDOW_DAYS + BASELINE_WINDOW_DAYS)
    recent_outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(recent_start))
    baseline_outcomes = repository.list_prediction_outcomes_between(
        _iso(baseline_start),
        _iso(recent_start),
    )
    predictions = repository.list_recent_model_predictions(limit=1000)
    indicators = repository.list_recent_indicators(limit=1000)

    recent_by_model = _group_by_model(recent_outcomes)
    baseline_by_model = _group_by_model(baseline_outcomes)
    predictions_by_model = _group_by_model(predictions)
    feature_drift = _feature_drift_score(indicators)

    assessments = [
        assessment
        for performance in repository.list_model_performance()
        if (
            assessment := assess_model_drift(
                performance,
                recent_by_model=recent_by_model,
                baseline_by_model=baseline_by_model,
                predictions_by_model=predictions_by_model,
                feature_drift=feature_drift,
                settings=settings,
            )
        )
    ]
    events_to_store = [
        assessment.to_row(as_of)
        for assessment in assessments
        if assessment.severity in {"medium", "high", "critical"}
    ]
    stored_events = repository.insert_model_drift_events(events_to_store)
    return {
        "models_checked": len(repository.list_model_performance()),
        "drift_events": len(stored_events),
        "assessments": [
            {
                "model_name": assessment.model_name,
                "drift_score": assessment.drift_score,
                "drift_type": assessment.drift_type,
                "severity": assessment.severity,
                "recommended_action": assessment.recommended_action,
                "components": assessment.components,
            }
            for assessment in assessments
        ],
    }


def model_weight_multipliers_from_events(
    events: Sequence[Mapping[str, Any]],
) -> dict[str, float]:
    multipliers: dict[str, float] = {}
    severity_multiplier = {
        "low": 0.85,
        "medium": 0.60,
        "high": 0.30,
        "critical": 0.0,
    }
    for event in events:
        model_name = event.get("model_name")
        if not model_name:
            continue
        multiplier = severity_multiplier.get(str(event.get("severity") or "low"), 1.0)
        current = multipliers.get(str(model_name), 1.0)
        multipliers[str(model_name)] = min(current, multiplier)
    return multipliers


def recent_model_weight_multipliers(
    repository: SupabaseRepository,
    as_of: datetime | None = None,
    lookback_days: int = DRIFT_EVENT_LOOKBACK_DAYS,
) -> dict[str, float]:
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    since = as_of - timedelta(days=lookback_days)
    events = repository.list_recent_model_drift_events(since_timestamp=_iso(since), limit=500)
    return model_weight_multipliers_from_events(events)


def build_drift_report(
    repository: SupabaseRepository | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    events = repository.list_recent_model_drift_events(limit=limit)
    multipliers = model_weight_multipliers_from_events(events)
    return {
        "events": events,
        "active_model_weight_multipliers": multipliers,
        "disabled_models": [
            model_name for model_name, multiplier in multipliers.items() if multiplier <= 0
        ],
    }
