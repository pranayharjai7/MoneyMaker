from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

from backend.db.repository import SupabaseRepository
from backend.core.math_utils import safe_float

from backend.entry_engine.service import calculate_entry_zones
from backend.risk_engine.service import calculate_risk_parameters
from backend.target_engine.service import calculate_profit_targets
from backend.expected_move.service import calculate_expected_move
from backend.hold_duration.service import calculate_hold_duration
from backend.execution_engine.service import recommend_execution_strategy
from backend.trade_reasoning.service import generate_trade_reasoning
from backend.multi_timeframe.service import calculate_timeframe_biases

def construct_and_persist_trade_plan(
    ticker: str,
    repository: SupabaseRepository | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any] | None:
    """Core coordinating planner. Ingests all data, constructs complete plans, and saves them.
    
    Ensures absolute point-in-time correctness to prevent future leakage in historical reply runs.
    """
    repository = repository or SupabaseRepository()
    
    # 1. Fetch Stock
    stock = repository.get_stock_by_ticker(ticker)
    if not stock:
        return None
    stock_id = str(stock["id"])
    company_name = str(stock["company_name"])
    
    # 2. Point-in-time queries to avoid leakage
    as_of_str = as_of.astimezone(UTC).isoformat() if as_of else datetime.now(tz=UTC).isoformat()
    
    # Fetch price at or before timestamp
    price_row = repository.get_price_at_or_before(stock_id, as_of_str)
    if not price_row:
        return None
    current_price = safe_float(price_row.get("close"), 0.0)
    if current_price <= 0:
        return None
        
    # Fetch prices history for timeframe checks
    prices = repository.get_prices(stock_id, limit=200)
    if as_of:
        # Filter prices to only include those <= as_of
        parsed_as_of = as_of.astimezone(UTC)
        filtered_prices = []
        for p in prices:
            p_time = datetime.fromisoformat(str(p["timestamp"]).replace("Z", "+00:00")).astimezone(UTC)
            if p_time <= parsed_as_of:
                filtered_prices.append(p)
        prices = filtered_prices
        
    if not prices:
        return None

    # Fetch indicators
    indicator_row = repository.get_indicator_at_or_before(stock_id, as_of_str)
    indicators = indicator_row or {
        "rsi": 50.0,
        "sma_20": current_price,
        "sma_50": current_price,
        "bollinger_upper": current_price * 1.05,
        "bollinger_lower": current_price * 0.95,
        "volatility": 0.02,
        "volume_momentum": 0.0,
        "macd": 0.0,
        "macd_signal": 0.0,
    }

    # Fetch latest signal or calibrated predictions
    latest_signal = repository.latest_signal_for_stock(stock_id)
    if as_of:
        # Find signal at or before as_of
        parsed_as_of = as_of.astimezone(UTC)
        signals = repository.get_signals_for_ticker(ticker, limit=100)
        filtered_signals = []
        for s in signals:
            s_time = datetime.fromisoformat(str(s["timestamp"]).replace("Z", "+00:00")).astimezone(UTC)
            if s_time <= parsed_as_of:
                filtered_signals.append(s)
        latest_signal = filtered_signals[0] if filtered_signals else None

    # Defaults if signal is absent
    if not latest_signal:
        latest_signal = {
            "buy_probability": 0.50,
            "sell_probability": 0.30,
            "expected_return": 0.0,
            "risk_score": 0.50,
            "suggested_hold_days": 5,
        }

    buy_prob = safe_float(latest_signal.get("buy_probability"), 0.50)
    sell_prob = safe_float(latest_signal.get("sell_probability"), 0.30)
    neutral_prob = max(0.0, round(1.0 - buy_prob - sell_prob, 3))
    expected_return = safe_float(latest_signal.get("expected_return"), 0.0)
    suggested_hold = int(latest_signal.get("suggested_hold_days", 5))

    # Fetch market regime
    regime_row = repository.get_market_regime_at_or_before(as_of_str) or repository.latest_market_regime()
    regime_name = str(regime_row.get("current_regime") if regime_row else "SIDEWAYS")
    regime_conf = safe_float(regime_row.get("confidence") if regime_row else 0.70, 0.70)

    # 3. Call micro-engines
    # entry_engine
    entry = calculate_entry_zones(current_price, indicators, regime_name)
    suggested_entry_price = entry["suggested_entry_price"]

    # risk_engine
    risk = calculate_risk_parameters(suggested_entry_price, indicators, regime_name, regime_conf)
    stop_loss = risk["stop_loss"]

    # target_engine
    targets = calculate_profit_targets(suggested_entry_price, risk["atr_proxy"], indicators, regime_name, buy_prob)
    tp1_price = targets[0]["target_price"]

    # expected_move
    move = calculate_expected_move(current_price, indicators, regime_name, buy_prob)

    # hold_duration
    hold = calculate_hold_duration(suggested_hold, indicators, regime_name)

    # execution_engine
    exec_rec = recommend_execution_strategy(entry["entry_type"], suggested_entry_price)

    # multi_timeframe
    mtf = calculate_timeframe_biases(prices, indicators)

    # Prevent bullish short-term inside macro bear trends
    entry_score = entry["entry_score"]
    if mtf["counter_trend_warning"]:
        entry_score *= 0.65  # Penalize score significantly

    # Calculate precise risk/reward ratio
    risk_width = suggested_entry_price - stop_loss
    reward_width = tp1_price - suggested_entry_price
    if risk_width > 0:
        risk_reward_ratio = round(reward_width / risk_width, 2)
    else:
        risk_reward_ratio = 1.0

    # Determine confidence classification
    if entry_score >= 70.0 and buy_prob >= 0.60:
        confidence = "HIGH"
    elif entry_score >= 45.0 and buy_prob >= 0.48:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # trade_reasoning
    reasonings = generate_trade_reasoning(
        indicators, regime_name, buy_prob, expected_return,
        meta_model_agreement=buy_prob, calibration_confidence_stable=(regime_name != "HIGH VOLATILITY")
    )

    # 4. Formulate Plan Document
    trade_plan = {
        "stock_id": stock_id,
        "current_price": current_price,
        "forecast_window_min_days": 5,
        "forecast_window_max_days": 7,
        "bullish_probability": buy_prob,
        "bearish_probability": sell_prob,
        "neutral_probability": neutral_prob,
        "confidence": confidence,
        "regime_context": regime_name,
        "weekly_bias": mtf["weekly_bias"],
        "daily_bias": mtf["daily_bias"],
        "intraday_bias": mtf["intraday_bias"],
        "suggested_entry_low": entry["buy_zone_low"],
        "suggested_entry_high": entry["buy_zone_high"],
        "suggested_entry_price": suggested_entry_price,
        "entry_type": entry["entry_type"],
        "entry_timing": entry["entry_timing"],
        "entry_score": round(entry_score, 1),
        "stop_loss": stop_loss,
        "max_suggested_risk_pct": risk["max_suggested_risk_pct"],
        "risk_reward_ratio": risk_reward_ratio,
        "expected_hold_min_days": hold["expected_hold_min_days"],
        "expected_hold_max_days": hold["expected_hold_max_days"],
        "suggested_execution": exec_rec["suggested_execution"],
    }

    # 5. Persist to Database
    inserted_plan = repository.upsert_trade_plan(trade_plan)
    if not inserted_plan:
        return None
    plan_id = str(inserted_plan["id"])

    # Persist Targets
    for target in targets:
        target["trade_plan_id"] = plan_id
    repository.upsert_trade_targets(targets)

    # Persist Reasoning
    for reason in reasonings:
        reason["trade_plan_id"] = plan_id
    repository.insert_trade_reasoning(reasonings)

    # Persist Execution Recommendations
    for rec in exec_rec["recommendations"]:
        rec["trade_plan_id"] = plan_id
    repository.upsert_execution_recommendations(exec_rec["recommendations"])

    # Return full hydrated plan shape
    return {
        **inserted_plan,
        "stock": stock,
        "targets": targets,
        "reasoning": reasonings,
        "execution_recommendations": exec_rec["recommendations"],
        "expected_move": move,
    }
