from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


DEFENSIVE_REGIMES = {"HIGH VOLATILITY", "LOW LIQUIDITY", "BEAR TREND"}


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    mode: str
    violations: list[str]
    adjusted_signal_type: str
    adjusted_expected_return: float
    adjusted_risk_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "violations": self.violations,
            "adjusted_signal_type": self.adjusted_signal_type,
            "adjusted_expected_return": self.adjusted_expected_return,
            "adjusted_risk_score": self.adjusted_risk_score,
        }


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _regime_name(regime: Mapping[str, Any] | None) -> str:
    return str((regime or {}).get("current_regime") or "SIDEWAYS")


def _defensive_mode(regime: Mapping[str, Any] | None, settings: Settings) -> bool:
    regime_name = _regime_name(regime)
    volatility = safe_float((regime or {}).get("volatility_proxy"))
    confidence = clamp(safe_float((regime or {}).get("confidence"), 0.0))
    return (
        regime_name in DEFENSIVE_REGIMES and confidence >= 0.55
    ) or volatility >= settings.guardrail_extreme_volatility_threshold


def evaluate_signal_guardrails(
    signal: Mapping[str, Any],
    regime: Mapping[str, Any] | None,
    daily_signal_count: int,
    settings: Settings | None = None,
) -> GuardrailDecision:
    settings = settings or get_settings()
    violations: list[str] = []
    signal_type = str(signal.get("signal_type") or "neutral")
    expected_return = safe_float(signal.get("expected_return"))
    risk_score = clamp(safe_float(signal.get("risk_score"), 0.5))
    mode = "normal"

    if daily_signal_count >= settings.guardrail_max_daily_signal_volume:
        violations.append("max_daily_signal_volume")

    if _defensive_mode(regime, settings):
        mode = "defensive"
        if signal_type == "buy" and risk_score > 0.45:
            violations.append("extreme_volatility_shutdown")
        if signal_type == "buy":
            expected_return *= 0.5
            risk_score = max(risk_score, 0.65)

    allowed = not violations
    adjusted_signal_type = signal_type if allowed else "neutral"
    adjusted_expected_return = expected_return if allowed else 0.0
    adjusted_risk_score = clamp(risk_score if allowed else max(risk_score, 0.85))
    return GuardrailDecision(
        allowed=allowed,
        mode=mode,
        violations=violations,
        adjusted_signal_type=adjusted_signal_type,
        adjusted_expected_return=adjusted_expected_return,
        adjusted_risk_score=adjusted_risk_score,
    )


def apply_guardrails_to_signal(
    signal: Mapping[str, Any],
    repository: SupabaseRepository,
    regime: Mapping[str, Any] | None,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], GuardrailDecision]:
    now = (now or datetime.now(tz=UTC)).astimezone(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_signal_count = repository.count_signals_since(_iso(day_start))
    decision = evaluate_signal_guardrails(
        signal,
        regime=regime,
        daily_signal_count=daily_signal_count,
        settings=settings,
    )
    adjusted = {
        **dict(signal),
        "signal_type": decision.adjusted_signal_type,
        "expected_return": decision.adjusted_expected_return,
        "risk_score": decision.adjusted_risk_score,
    }
    if decision.adjusted_signal_type == "neutral":
        adjusted["buy_probability"] = min(safe_float(adjusted.get("buy_probability"), 0.5), 0.5)
        adjusted["sell_probability"] = min(safe_float(adjusted.get("sell_probability"), 0.5), 0.5)
    return adjusted, decision


def build_signal_audit_row(
    signal: Mapping[str, Any],
    predictions: Sequence[Mapping[str, Any]],
    regime: Mapping[str, Any] | None,
    calibrated_by_prediction_id: Mapping[str, Mapping[str, Any]],
    meta_model_output: Mapping[str, Any],
    guardrail_decision: GuardrailDecision,
) -> dict[str, Any]:
    calibration_values = {
        prediction_id: {
            "calibrated_probability": row.get("calibrated_probability"),
            "calibration_method": row.get("calibration_method"),
        }
        for prediction_id, row in calibrated_by_prediction_id.items()
    }
    return {
        "stock_id": signal["stock_id"],
        "timestamp": signal["timestamp"],
        "models_involved": [
            {
                "model_name": prediction.get("model_name"),
                "probability_up": prediction.get("probability_up"),
                "expected_return": prediction.get("expected_return"),
                "confidence": prediction.get("confidence"),
            }
            for prediction in predictions
        ],
        "regime": (regime or {}).get("current_regime"),
        "calibration_values": calibration_values,
        "final_meta_model_output": dict(meta_model_output),
        "guardrail_decision": guardrail_decision.to_dict(),
    }


def build_guardrail_report(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    audits = repository.list_signal_audit_logs(limit=100)
    blocked = [
        row
        for row in audits
        if isinstance(row.get("guardrail_decision"), Mapping)
        and not row["guardrail_decision"].get("allowed", True)
    ]
    return {
        "recent_audits": audits,
        "blocked_signal_count": len(blocked),
        "recent_violations": [
            violation
            for row in blocked
            for violation in row.get("guardrail_decision", {}).get("violations", [])
        ],
    }
