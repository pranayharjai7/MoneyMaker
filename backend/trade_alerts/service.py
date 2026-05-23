from __future__ import annotations

from typing import Any, Sequence
from backend.core.math_utils import safe_float

def generate_lifecycle_alerts(
    ticker: str,
    current_price: float,
    trade_plan: dict[str, Any],
    targets: Sequence[dict[str, Any]],
    regime: str,
) -> list[dict[str, Any]]:
    """Determine if any trade lifecycle alerts should be fired based on current price.
    
    Returns:
        list[dict]: List of generated alerts, each with 'alert_type', 'message', and 'triggered_at' placeholder.
    """
    alerts = []
    
    buy_low = safe_float(trade_plan.get("suggested_entry_low"))
    buy_high = safe_float(trade_plan.get("suggested_entry_high"))
    stop_loss = safe_float(trade_plan.get("stop_loss"))
    
    # 1. Entry Zone Alert
    if buy_low > 0 and buy_high > 0 and buy_low <= current_price <= buy_high:
        alerts.append({
            "alert_type": "entry",
            "message": f"{ticker} has entered the ideal buy entry zone [{buy_low:.2f} - {buy_high:.2f}]. Suggested entry: {trade_plan.get('suggested_entry_price'):.2f}.",
        })
        
    # 2. Risk Stop-Loss Alert
    if stop_loss > 0 and current_price <= stop_loss:
        alerts.append({
            "alert_type": "risk",
            "message": f"{ticker} has breached the key protective stop-loss level of {stop_loss:.2f}! Immediate defensive risk mitigation required.",
        })
        
    # 3. Take Profit Exit Alerts
    for target in targets:
        target_price = safe_float(target.get("target_price"))
        label = target.get("target_label", "TP")
        if target_price > 0 and current_price >= target_price:
            alerts.append({
                "alert_type": "exit",
                "message": f"{ticker} take-profit target {label} was reached at {target_price:.2f}! Consider scaling out of the position.",
            })

    # 4. Regime Alert (dynamic check)
    current_regime = regime
    previous_regime = trade_plan.get("regime_context")
    if current_regime != previous_regime:
        alerts.append({
            "alert_type": "regime",
            "message": f"Market regime shift detected: {ticker} environment transitioned from '{previous_regime}' to '{current_regime}'. Re-evaluate risk parameters.",
        })

    return alerts
