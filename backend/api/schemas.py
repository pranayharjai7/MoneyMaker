from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StockOut(BaseModel):
    id: str
    ticker: str
    company_name: str
    sector: str | None = None
    exchange: str | None = None
    created_at: datetime | None = None


class SignalOut(BaseModel):
    id: str | None = None
    stock_id: str
    timestamp: datetime
    buy_probability: float
    sell_probability: float
    expected_return: float
    risk_score: float
    suggested_hold_days: int
    signal_type: str
    stock: StockOut | None = None


class WatchlistItemOut(BaseModel):
    id: str
    user_id: str
    stock_id: str
    created_at: datetime
    stock: StockOut | None = None


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)


class PortfolioItemOut(BaseModel):
    id: str
    user_id: str
    stock_id: str
    shares: float
    average_price: float
    created_at: datetime
    stock: StockOut | None = None


class PortfolioWeightOut(BaseModel):
    id: str | None = None
    run_id: str | None = None
    stock_id: str
    ticker: str
    sector: str | None = None
    allocation: float
    expected_return: float
    risk_score: float
    volatility: float
    signal_timestamp: datetime
    optimizer_method: str = "fractional_kelly_vol_scaled"
    rationale: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    stock: StockOut | None = None


class AlertOut(BaseModel):
    id: str
    user_id: str
    stock_id: str
    alert_type: str
    probability: float
    expected_return: float
    risk_score: float
    created_at: datetime
    is_read: bool
    stock: StockOut | None = None


class AlertsReadRequest(BaseModel):
    alert_ids: list[str] = Field(default_factory=list)


class ModelPerformanceOut(BaseModel):
    model_name: str
    accuracy: float
    brier_score: float
    calibration_error: float
    sharpe_contribution: float
    sample_size: int = 0
    window_days: int = 90
    updated_at: datetime | None = None


class FeedbackSummaryOut(BaseModel):
    total_outcomes: int
    success_rate: float
    average_error: float
    average_absolute_error: float
    horizons: list[int]
    models_tracked: int
    window_days: int
    latest_evaluated_at: datetime | None = None


class CalibrationModelStatusOut(BaseModel):
    model_name: str
    calibration_method: str
    sample_size: int
    calibration_error: float


class CalibrationStatusOut(BaseModel):
    status: str
    models: list[CalibrationModelStatusOut]
    window_days: int
    latest_calibrated_at: datetime | None = None


class MarketRegimeOut(BaseModel):
    timestamp: datetime
    current_regime: str
    confidence: float
    spx_trend: float
    volatility_proxy: float
    moving_average_spread: float
    sector_correlation_shift: float
    liquidity_score: float
    feature_payload: dict[str, Any] = Field(default_factory=dict)


class BacktestResultOut(BaseModel):
    id: str | None = None
    strategy_return: float
    max_drawdown: float
    sharpe_ratio: float
    trade_count: int
    win_rate: float
    max_win_streak: int
    max_loss_streak: int
    total_transaction_costs: float
    average_slippage_bps: float
    parameters: dict[str, Any] = Field(default_factory=dict)
    result_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class StatusOut(BaseModel):
    status: str


def with_stock_alias(row: dict[str, Any]) -> dict[str, Any]:
    if "stocks" in row and "stock" not in row:
        return {**row, "stock": row.get("stocks")}
    return row


class TargetOut(BaseModel):
    id: str | None = None
    trade_plan_id: str | None = None
    target_label: str
    target_price: float = Field(..., alias="price")
    probability: float
    created_at: datetime | None = None

    class Config:
        populate_by_name = True


class ReasoningOut(BaseModel):
    id: str | None = None
    trade_plan_id: str | None = None
    factor_type: str
    factor_text: str
    created_at: datetime | None = None


class RecommendationOut(BaseModel):
    id: str | None = None
    trade_plan_id: str | None = None
    situation: str
    suggested_order_type: str
    order_price: float
    reason: str
    created_at: datetime | None = None


class ExpectedMoveOut(BaseModel):
    expected_upside_pct: float
    expected_downside_pct: float
    confidence_interval_low: float
    confidence_interval_high: float


class TradePlanOut(BaseModel):
    id: str
    stock_id: str
    current_price: float
    forecast_window_min_days: int
    forecast_window_max_days: int
    bullish_probability: float
    bearish_probability: float
    neutral_probability: float
    confidence: str
    regime_context: str
    weekly_bias: str
    daily_bias: str
    intraday_bias: str
    suggested_entry_low: float
    suggested_entry_high: float
    suggested_entry_price: float
    entry_type: str
    entry_timing: str
    entry_score: float
    stop_loss: float
    max_suggested_risk_pct: float
    risk_reward_ratio: float
    expected_hold_min_days: int
    expected_hold_max_days: int
    suggested_execution: str
    created_at: datetime
    stock: StockOut | None = None


class TradePlanDetailOut(TradePlanOut):
    targets: list[TargetOut] = Field(default_factory=list)
    reasoning: list[ReasoningOut] = Field(default_factory=list)
    execution_recommendations: list[RecommendationOut] = Field(default_factory=list)
    expected_move: ExpectedMoveOut | None = None


class TradeStopUpdateOut(BaseModel):
    id: str
    trade_plan_id: str
    old_stop_price: float
    new_stop_price: float
    reason: str
    updated_at: datetime


class TradeAlertOut(BaseModel):
    id: str
    trade_plan_id: str
    alert_type: str
    message: str
    triggered_at: datetime
    is_read: bool


class RiskAnalysisOut(BaseModel):
    ticker: str
    suggested_entry_price: float
    stop_loss: float
    max_suggested_risk_pct: float
    risk_reward_ratio: float
    trailing_stop: str


class TimeframeAnalysisOut(BaseModel):
    ticker: str
    weekly: str
    daily: str
    intraday: str
    counter_trend_warning: bool

