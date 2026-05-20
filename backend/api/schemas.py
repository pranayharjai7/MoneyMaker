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
