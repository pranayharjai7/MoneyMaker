from __future__ import annotations

from backend.entry_engine.service import calculate_entry_zones
from backend.risk_engine.service import calculate_risk_parameters
from backend.target_engine.service import calculate_profit_targets
from backend.expected_move.service import calculate_expected_move
from backend.hold_duration.service import calculate_hold_duration
from backend.execution_engine.service import recommend_execution_strategy
from backend.trade_reasoning.service import generate_trade_reasoning
from backend.trade_alerts.service import generate_lifecycle_alerts
from backend.multi_timeframe.service import calculate_timeframe_biases

def test_entry_engine_calculates_correct_zones() -> None:
    current_price = 100.0
    indicators = {
        "rsi": 25.0,
        "sma_20": 100.0,
        "sma_50": 105.0,
        "bollinger_upper": 110.0,
        "bollinger_lower": 95.0,
        "volume_momentum": 0.05,
    }
    # Sideways + oversold RSI implies Mean Reversion
    entry = calculate_entry_zones(current_price, indicators, "SIDEWAYS")
    assert entry["entry_type"] == "Mean Reversion"
    assert entry["buy_zone_low"] <= entry["buy_zone_high"]
    assert entry["buy_zone_low"] <= entry["suggested_entry_price"] <= entry["buy_zone_high"]
    assert entry["entry_score"] > 40.0

def test_risk_engine_stop_loss_bounds() -> None:
    current_price = 100.0
    indicators = {
        "volatility": 0.03,  # 3% daily volatility
    }
    risk = calculate_risk_parameters(current_price, indicators, "BULL TREND")
    # Stop loss should be reasonably below entry but capped
    assert risk["stop_loss"] < current_price
    assert current_price * 0.92 <= risk["stop_loss"] <= current_price * 0.985
    assert 0.5 <= risk["max_suggested_risk_pct"] <= 3.0

def test_target_engine_generates_correct_ranking() -> None:
    entry_price = 100.0
    atr_proxy = 3.0
    indicators = {}
    
    targets = calculate_profit_targets(entry_price, atr_proxy, indicators, "BULL TREND", 0.75)
    
    assert len(targets) == 3
    assert targets[0]["target_label"] == "TP1"
    assert targets[1]["target_label"] == "TP2"
    assert targets[2]["target_label"] == "TP3"
    
    assert targets[0]["target_price"] < targets[1]["target_price"] < targets[2]["target_price"]
    assert targets[0]["probability"] > targets[1]["probability"] > targets[2]["probability"]

def test_expected_move_calculates_asymmetry() -> None:
    price = 100.0
    indicators = {"volatility": 0.02}
    
    # Bullish bias tilts upside move wider
    bull_move = calculate_expected_move(price, indicators, "BULL TREND", 0.80)
    bear_move = calculate_expected_move(price, indicators, "BEAR TREND", 0.20)
    
    assert bull_move["expected_upside_pct"] > bull_move["expected_downside_pct"]
    assert bear_move["expected_downside_pct"] > bear_move["expected_upside_pct"]

def test_hold_duration_bounds() -> None:
    indicators = {"volatility": 0.02}
    
    duration = calculate_hold_duration(5, indicators, "BULL TREND")
    assert 1 <= duration["expected_hold_min_days"] < duration["expected_hold_max_days"] <= 20

def test_execution_engine_recommends_correct_orders() -> None:
    breakout_rec = recommend_execution_strategy("Breakout", 105.0)
    assert breakout_rec["suggested_execution"] == "Stop order at 105.00"
    assert breakout_rec["recommendations"][0]["suggested_order_type"] == "stop"
    
    pullback_rec = recommend_execution_strategy("Pullback", 98.0)
    assert pullback_rec["suggested_execution"] == "Limit order at 98.00"
    assert pullback_rec["recommendations"][0]["suggested_order_type"] == "limit"

def test_trade_reasoning_generates_bullet_points() -> None:
    indicators = {
        "rsi": 62.0,
        "volume_momentum": 0.20,
    }
    reasons = generate_trade_reasoning(indicators, "BULL TREND", 0.74, 0.05)
    assert len(reasons) >= 3
    types = [r["factor_type"] for r in reasons]
    assert "regime" in types
    assert "momentum" in types

def test_lifecycle_alerts_fire() -> None:
    plan = {
        "suggested_entry_low": 98.0,
        "suggested_entry_high": 102.0,
        "suggested_entry_price": 100.0,
        "stop_loss": 94.0,
        "regime_context": "BULL TREND",
    }
    targets = [
        {"target_label": "TP1", "target_price": 106.0},
    ]
    
    # 1. Price in buy zone
    buy_alerts = generate_lifecycle_alerts("AAPL", 100.0, plan, targets, "BULL TREND")
    assert len(buy_alerts) == 1
    assert buy_alerts[0]["alert_type"] == "entry"
    
    # 2. Price breaches stop
    stop_alerts = generate_lifecycle_alerts("AAPL", 93.0, plan, targets, "BULL TREND")
    assert any(a["alert_type"] == "risk" for a in stop_alerts)
    
    # 3. Price hits target
    target_alerts = generate_lifecycle_alerts("AAPL", 107.0, plan, targets, "BULL TREND")
    assert any(a["alert_type"] == "exit" for a in target_alerts)

def test_multi_timeframe_checks() -> None:
    prices = [
        {"close": 100.0 + i * 0.1} for i in range(150)
    ]
    indicators = {
        "sma_20": 110.0,
        "sma_50": 105.0,
        "rsi": 60.0,
        "macd": 2.0,
        "macd_signal": 1.0,
    }
    
    mtf = calculate_timeframe_biases(prices, indicators)
    assert mtf["weekly_bias"] in ("Bullish", "Bearish", "Neutral")
    assert mtf["daily_bias"] in ("Bullish", "Bearish", "Neutral")
    assert mtf["intraday_bias"] in ("Bullish", "Bearish", "Neutral")
