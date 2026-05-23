from __future__ import annotations

from backend.historical_signals.service import build_calibration_rows_from_replay
from backend.replay_analytics.service import (
    build_replay_performance_report,
    equity_curve_from_outcomes,
    strategy_contribution_analysis,
)


def test_build_calibration_rows_from_replay() -> None:
    signals = [
        {
            "id": "sig-1",
            "stock_id": "stock-1",
            "timestamp": "2023-01-05T21:00:00+00:00",
            "model_predictions": [
                {"model_name": "momentum", "probability_up": 0.7, "expected_return": 0.04}
            ],
        }
    ]
    outcomes = [
        {
            "historical_signal_id": "sig-1",
            "actual_return": 0.05,
        }
    ]
    rows = build_calibration_rows_from_replay(signals, outcomes)
    assert len(rows) == 1
    assert rows[0]["model_name"] == "momentum"
    assert rows[0]["actual_return"] == 0.05


def test_equity_curve_from_outcomes_compounds() -> None:
    curve = equity_curve_from_outcomes(
        [
            {"exit_timestamp": "2023-02-01T21:00:00+00:00", "actual_return": 0.1, "outcome": "win"},
            {"exit_timestamp": "2023-03-01T21:00:00+00:00", "actual_return": -0.05, "outcome": "loss"},
        ],
        initial_equity=100_000.0,
    )
    assert len(curve) == 3
    assert curve[-1]["equity"] != 100_000.0


def test_strategy_contribution_analysis() -> None:
    rows = strategy_contribution_analysis(
        [
            {
                "model_predictions": [
                    {"model_name": "momentum", "probability_up": 0.7, "expected_return": 0.03},
                    {"model_name": "mean_reversion", "probability_up": 0.4, "expected_return": -0.01},
                ]
            }
        ]
    )
    assert len(rows) == 2
    assert rows[0]["model_name"] in {"momentum", "mean_reversion"}


class FakeAnalyticsRepository:
    def __init__(self) -> None:
        self.run = {
            "id": "run-1",
            "universe_name": "etf_only",
            "mode": "signal_only",
            "status": "completed",
            "signals_generated": 2,
            "outcomes_evaluated": 2,
        }

    def get_replay_run(self, replay_run_id: str) -> dict | None:
        return self.run if replay_run_id == "run-1" else None

    def list_historical_signals(self, *, replay_run_id: str, limit: int = 1000) -> list[dict]:
        return [
            {
                "id": "sig-1",
                "regime": "BULL TREND",
                "model_predictions": [{"model_name": "momentum", "probability_up": 0.7, "expected_return": 0.03}],
            }
        ]

    def list_replay_outcomes(self, *, replay_run_id: str, limit: int = 1000) -> list[dict]:
        return [
            {
                "historical_signal_id": "sig-1",
                "actual_return": 0.04,
                "exit_timestamp": "2023-02-01T21:00:00+00:00",
                "outcome": "win",
            },
            {
                "historical_signal_id": "sig-2",
                "actual_return": -0.02,
                "exit_timestamp": "2023-03-01T21:00:00+00:00",
                "outcome": "loss",
            },
        ]

    def list_replay_portfolio_snapshots(self, *, replay_run_id: str, limit: int = 5000) -> list[dict]:
        return []

    def list_historical_calibration_snapshots(self, *, replay_run_id: str, limit: int = 5000) -> list[dict]:
        return [
            {
                "as_of_date": "2023-02-01",
                "model_name": "momentum",
                "calibration_method": "isotonic_regression",
                "calibration_error": 0.05,
                "sample_size": 40,
            }
        ]


def test_build_replay_performance_report() -> None:
    report = build_replay_performance_report("run-1", repository=FakeAnalyticsRepository())
    assert report["replay_run_id"] == "run-1"
    assert report["win_rate"] == 0.5
    assert len(report["equity_curve"]) >= 2
    assert report["strategy_contribution"]
