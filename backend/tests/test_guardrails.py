from __future__ import annotations

from backend.core.config import Settings
from backend.guardrails.service import (
    apply_guardrails_to_signal,
    build_guardrail_report,
    build_signal_audit_row,
    evaluate_signal_guardrails,
)


class FakeGuardrailRepository:
    def count_signals_since(self, since_timestamp: str) -> int:
        assert since_timestamp
        return 99

    def list_signal_audit_logs(self, limit: int = 100):
        return [
            {
                "guardrail_decision": {
                    "allowed": False,
                    "violations": ["max_daily_signal_volume"],
                }
            },
            {"guardrail_decision": {"allowed": True, "violations": []}},
        ][:limit]


def test_guardrails_neutralize_aggressive_signal_in_extreme_volatility() -> None:
    signal = {
        "stock_id": "stock-1",
        "timestamp": "2026-05-21T21:00:00+00:00",
        "signal_type": "buy",
        "expected_return": 0.05,
        "risk_score": 0.7,
    }

    decision = evaluate_signal_guardrails(
        signal,
        regime={"current_regime": "HIGH VOLATILITY", "confidence": 0.8, "volatility_proxy": 0.5},
        daily_signal_count=0,
        settings=Settings(guardrail_extreme_volatility_threshold=0.45),
    )

    assert not decision.allowed
    assert decision.adjusted_signal_type == "neutral"
    assert "extreme_volatility_shutdown" in decision.violations


def test_signal_audit_row_is_traceable() -> None:
    decision = evaluate_signal_guardrails(
        {"signal_type": "neutral", "expected_return": 0.0, "risk_score": 0.4},
        regime={"current_regime": "SIDEWAYS"},
        daily_signal_count=0,
    )

    audit = build_signal_audit_row(
        signal={"stock_id": "stock-1", "timestamp": "2026-05-21T21:00:00+00:00"},
        predictions=[
            {
                "model_name": "momentum",
                "probability_up": 0.66,
                "expected_return": 0.02,
                "confidence": 0.7,
            }
        ],
        regime={"current_regime": "SIDEWAYS"},
        calibrated_by_prediction_id={
            "prediction-1": {
                "calibrated_probability": 0.63,
                "calibration_method": "isotonic_regression",
            }
        },
        meta_model_output={"buy_probability": 0.64},
        guardrail_decision=decision,
    )

    assert audit["models_involved"][0]["model_name"] == "momentum"
    assert audit["regime"] == "SIDEWAYS"
    assert audit["calibration_values"]["prediction-1"]["calibrated_probability"] == 0.63
    assert audit["guardrail_decision"]["allowed"]


def test_apply_guardrails_caps_daily_signal_volume_and_reports_violations() -> None:
    repository = FakeGuardrailRepository()
    signal = {
        "stock_id": "stock-1",
        "timestamp": "2026-05-21T21:00:00+00:00",
        "signal_type": "buy",
        "buy_probability": 0.9,
        "sell_probability": 0.1,
        "expected_return": 0.04,
        "risk_score": 0.2,
    }

    adjusted, decision = apply_guardrails_to_signal(
        signal,
        repository=repository,
        regime={"current_regime": "SIDEWAYS"},
        settings=Settings(guardrail_max_daily_signal_volume=10),
    )
    report = build_guardrail_report(repository=repository)

    assert not decision.allowed
    assert adjusted["signal_type"] == "neutral"
    assert adjusted["buy_probability"] == 0.5
    assert report["blocked_signal_count"] == 1
    assert report["recent_violations"] == ["max_daily_signal_volume"]
