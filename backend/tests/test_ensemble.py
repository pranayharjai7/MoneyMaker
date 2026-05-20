from __future__ import annotations

from backend.ensemble.service import combine_model_outputs


def test_combine_model_outputs_generates_buy_signal() -> None:
    signal = combine_model_outputs(
        stock_id="stock-1",
        timestamp="2026-05-19T21:00:00+00:00",
        predictions=[
            {
                "model_name": "momentum",
                "probability_up": 0.82,
                "expected_return": 0.07,
                "confidence": 0.85,
            },
            {
                "model_name": "volatility_breakout",
                "probability_up": 0.75,
                "expected_return": 0.05,
                "confidence": 0.75,
            },
            {
                "model_name": "sentiment",
                "probability_up": 0.72,
                "expected_return": 0.04,
                "confidence": 0.65,
            },
        ],
        latest_indicator={"volatility": 0.02},
    )

    assert signal.signal_type == "buy"
    assert signal.buy_probability > signal.sell_probability
    assert signal.expected_return > 0

