from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from backend.core.math_utils import clamp, safe_float


@dataclass
class PaperPortfolio:
    cash: float = 100_000.0
    positions: dict[str, dict[str, Any]] = field(default_factory=dict)

    def equity(self, marks: dict[str, float]) -> float:
        holdings = sum(
            safe_float(position.get("shares")) * marks.get(stock_id, safe_float(position.get("entry_price")))
            for stock_id, position in self.positions.items()
        )
        return self.cash + holdings

    def process_signal(
        self,
        signal: dict[str, Any],
        *,
        marks: dict[str, float],
        max_position_pct: float = 0.1,
    ) -> None:
        stock_id = str(signal["stock_id"])
        signal_type = str(signal.get("signal_type"))
        mark = marks.get(stock_id)
        if mark is None or mark <= 0:
            return

        if signal_type == "sell" and stock_id in self.positions:
            position = self.positions.pop(stock_id)
            self.cash += safe_float(position.get("shares")) * mark
            return

        if signal_type != "buy":
            return

        risk_score = clamp(safe_float(signal.get("risk_score"), 0.5))
        allocation = clamp((1.0 - risk_score) * max_position_pct, 0.02, max_position_pct)
        budget = self.cash * allocation
        if budget <= 0:
            return
        shares = budget / mark
        self.cash -= budget
        self.positions[stock_id] = {
            "shares": shares,
            "entry_price": mark,
            "entry_signal_timestamp": signal.get("timestamp"),
        }

    def snapshot(self, snapshot_date: date, marks: dict[str, float]) -> dict[str, Any]:
        return {
            "snapshot_date": snapshot_date.isoformat(),
            "cash": self.cash,
            "equity": self.equity(marks),
            "positions": [
                {"stock_id": stock_id, **position, "mark": marks.get(stock_id)}
                for stock_id, position in self.positions.items()
            ],
        }
