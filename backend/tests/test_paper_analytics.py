from __future__ import annotations

from typing import Any

from backend.paper_analytics.service import build_paper_performance_report


class FakePaperAnalyticsRepository:
    def latest_backtest_result(self) -> dict[str, Any]:
        return {
            "strategy_return": 0.128,
            "max_drawdown": -0.041,
            "sharpe_ratio": 1.72,
            "trade_count": 2,
            "win_rate": 0.5,
            "result_payload": {
                "equity_curve": [1.0, 1.03, 1.01],
                "trades": [
                    {
                        "entry_timestamp": "2026-05-01T21:00:00+00:00",
                        "exit_timestamp": "2026-05-03T21:00:00+00:00",
                        "contribution": 0.03,
                    },
                    {
                        "entry_timestamp": "2026-05-05T21:00:00+00:00",
                        "exit_timestamp": "2026-05-06T21:00:00+00:00",
                        "contribution": -0.02,
                    },
                ],
            },
        }

    def get_market_regime_at_or_before(self, timestamp: str) -> dict[str, Any]:
        if timestamp < "2026-05-04":
            return {"current_regime": "BULL TREND"}
        return {"current_regime": "SIDEWAYS"}


def test_paper_analytics_builds_mobile_ready_performance_report() -> None:
    report = build_paper_performance_report(repository=FakePaperAnalyticsRepository())

    assert report["portfolio_return"] == 0.128
    assert report["sharpe_ratio"] == 1.72
    assert report["max_drawdown"] == -0.041
    assert report["daily_pnl"][0] == {"date": "2026-05-03", "pnl": 0.03}
    assert report["equity_curve"][-1]["cumulative_return"] == 0.010000000000000009
    assert {row["regime"] for row in report["regime_adjusted_returns"]} == {
        "BULL TREND",
        "SIDEWAYS",
    }
