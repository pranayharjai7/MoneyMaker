from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.db.repository import SupabaseRepository
from backend.db.supabase_client import get_supabase_client
from backend.api.schemas import (
    TradePlanOut,
    TradePlanDetailOut,
    RiskAnalysisOut,
    TimeframeAnalysisOut,
    TradeAlertOut,
    with_stock_alias,
)
from backend.trade_planner.service import construct_and_persist_trade_plan

router = APIRouter(tags=["trade_planning"])

@router.get("/trade-plans", response_model=list[TradePlanOut])
def list_trade_plans(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict[str, Any]]:
    plans = repository.list_trade_plans(limit=50)
    return [with_stock_alias(plan) for plan in plans]

@router.get("/trade-plans/{ticker}", response_model=TradePlanDetailOut)
def get_trade_plan_details(
    ticker: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict[str, Any]:
    ticker_upper = ticker.upper()
    stock = repository.get_stock_by_ticker(ticker_upper)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock ticker not found.")
        
    stock_id = str(stock["id"])
    plan = repository.get_latest_trade_plan(stock_id)
    
    # If a plan does not exist, trigger construct_and_persist_trade_plan on demand
    if not plan:
        plan = construct_and_persist_trade_plan(ticker_upper, repository=repository)
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="Unable to generate trade plan due to insufficient stock history."
            )
        # Under on-demand construction, return the completed hydrated plan dictionary directly
        return with_stock_alias(plan)

    plan_id = str(plan["id"])
    
    # Retrieve relations
    targets = repository.get_trade_targets(plan_id)
    reasoning = repository.get_trade_reasoning(plan_id)
    recs = repository.get_execution_recommendations(plan_id)
    
    # Ingest indicators and signal inputs to formulate Expected Move in response
    latest_signal = repository.latest_signal_for_stock(stock_id) or {}
    indicator_row = repository.get_indicator_at_or_before(stock_id, plan["created_at"]) or {}
    
    from backend.expected_move.service import calculate_expected_move
    move = calculate_expected_move(
        plan["current_price"],
        indicator_row,
        plan["regime_context"],
        float(latest_signal.get("buy_probability", 0.50))
    )

    return with_stock_alias({
        **plan,
        "stock": stock,
        "targets": targets,
        "reasoning": reasoning,
        "execution_recommendations": recs,
        "expected_move": move,
    })

@router.get("/risk-analysis/{ticker}", response_model=RiskAnalysisOut)
def get_risk_analysis(
    ticker: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict[str, Any]:
    ticker_upper = ticker.upper()
    stock = repository.get_stock_by_ticker(ticker_upper)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock ticker not found.")
        
    stock_id = str(stock["id"])
    plan = repository.get_latest_trade_plan(stock_id)
    
    if not plan:
        plan = construct_and_persist_trade_plan(ticker_upper, repository=repository)
        if not plan:
            raise HTTPException(status_code=400, detail="Insufficient price data to perform risk analysis.")
            
    # Trailing stop explanation logic
    indicator_row = repository.get_indicator_at_or_before(stock_id, plan["created_at"]) or {}
    from backend.risk_engine.service import calculate_risk_parameters
    risk = calculate_risk_parameters(plan["suggested_entry_price"], indicator_row, plan["regime_context"])

    return {
        "ticker": ticker_upper,
        "suggested_entry_price": plan["suggested_entry_price"],
        "stop_loss": plan["stop_loss"],
        "max_suggested_risk_pct": plan["max_suggested_risk_pct"],
        "risk_reward_ratio": plan["risk_reward_ratio"],
        "trailing_stop": risk["trailing_stop_desc"],
    }

@router.get("/timeframes/{ticker}", response_model=TimeframeAnalysisOut)
def get_timeframe_analysis(
    ticker: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict[str, Any]:
    ticker_upper = ticker.upper()
    stock = repository.get_stock_by_ticker(ticker_upper)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock ticker not found.")
        
    stock_id = str(stock["id"])
    plan = repository.get_latest_trade_plan(stock_id)
    
    if not plan:
        plan = construct_and_persist_trade_plan(ticker_upper, repository=repository)
        if not plan:
            raise HTTPException(status_code=400, detail="Insufficient price data to perform timeframe analysis.")

    # Calculate points of incongruency warnings
    from backend.multi_timeframe.service import calculate_timeframe_biases
    prices = repository.get_prices(stock_id, limit=200)
    indicator_row = repository.get_indicator_at_or_before(stock_id, plan["created_at"]) or {}
    mtf = calculate_timeframe_biases(prices, indicator_row)

    return {
        "ticker": ticker_upper,
        "weekly": plan["weekly_bias"],
        "daily": plan["daily_bias"],
        "intraday": plan["intraday_bias"],
        "counter_trend_warning": mtf["counter_trend_warning"],
    }

@router.get("/trade-alerts", response_model=list[TradeAlertOut])
def get_trade_alerts(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict[str, Any]]:
    # Retrieve all active trade lifecycle alerts
    return repository.get_trade_alerts(limit=50)
