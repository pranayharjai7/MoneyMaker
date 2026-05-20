from __future__ import annotations

from backend.alerts.service import should_generate_buy_alert
from backend.core.config import Settings


def test_buy_alert_rule_requires_probability_return_and_risk() -> None:
    settings = Settings(
        alert_min_buy_probability=0.65,
        alert_min_expected_return=0.03,
        alert_max_risk_score=0.55,
    )
    assert should_generate_buy_alert(
        {"buy_probability": 0.7, "expected_return": 0.04, "risk_score": 0.3},
        settings,
    )
    assert not should_generate_buy_alert(
        {"buy_probability": 0.7, "expected_return": 0.01, "risk_score": 0.3},
        settings,
    )

