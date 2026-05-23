from __future__ import annotations

from typing import Any

def recommend_execution_strategy(
    entry_type: str,
    suggested_entry_price: float,
) -> dict[str, Any]:
    """Recommend optimal execution parameters and order types.
    
    Returns:
        dict: Containing 'suggested_execution' description and 'recommendations' list of dictionaries.
    """
    recommendations = []
    
    if entry_type == "Breakout":
        suggested_order_type = "stop"
        suggested_execution = f"Stop order at {suggested_entry_price:.2f}"
        situation = "Momentum Breakout Confirmation"
        reason = "Place buy stop above current price resistance to confirm the volume expansion breakout and avoid pre-breakout noise."
        recommendations.append({
            "situation": situation,
            "suggested_order_type": suggested_order_type,
            "order_price": suggested_entry_price,
            "reason": reason,
        })
    elif entry_type == "Pullback":
        suggested_order_type = "limit"
        suggested_execution = f"Limit order at {suggested_entry_price:.2f}"
        situation = "Intraday Pullback to Support"
        reason = "Place limit order at key moving average support (20-day SMA) to capture local mean-reverting entry point."
        recommendations.append({
            "situation": situation,
            "suggested_order_type": suggested_order_type,
            "order_price": suggested_entry_price,
            "reason": reason,
        })
    elif entry_type == "Mean Reversion":
        suggested_order_type = "limit"
        suggested_execution = f"Limit order at {suggested_entry_price:.2f}"
        situation = "Support Extreme Limit"
        reason = "Oversold extreme condition near the Bollinger Lower Band. Place limit order at support level to capitalize on high-probability rebound."
        recommendations.append({
            "situation": situation,
            "suggested_order_type": suggested_order_type,
            "order_price": suggested_entry_price,
            "reason": reason,
        })
    else:  # Momentum Continuation
        suggested_order_type = "market"
        suggested_execution = f"Market order around {suggested_entry_price:.2f}"
        situation = "Urgent Momentum Acceleration"
        reason = "High probability trend persistence active. Enter immediately via market order to capture immediate upside swing before targets are reached."
        recommendations.append({
            "situation": situation,
            "suggested_order_type": suggested_order_type,
            "order_price": suggested_entry_price,
            "reason": reason,
        })

    return {
        "suggested_execution": suggested_execution,
        "recommendations": recommendations,
    }
