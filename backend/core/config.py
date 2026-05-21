from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MoneyMaker AI Trading Backend"
    environment: str = "local"
    api_prefix: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None
    jwt_audience: str | None = "authenticated"

    redis_url: str = "redis://localhost:6379/0"

    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    polygon_api_key: str | None = None
    market_data_timeout_seconds: float = 20.0

    default_tickers: str = Field(
        default="AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,JPM,UNH,V"
    )

    alert_min_buy_probability: float = 0.65
    alert_min_expected_return: float = 0.03
    alert_max_risk_score: float = 0.55

    notification_max_buy_signals_per_day: int = 5
    notification_max_sell_alerts_per_day: int = 5
    notification_cooldown_hours_per_stock: int = 12
    notification_default_min_probability: float = 0.62
    notification_high_volatility_min_probability: float = 0.72

    drift_min_accuracy: float = 0.52
    drift_min_sharpe_ratio: float = 0.15
    drift_max_calibration_error: float = 0.18
    drift_prediction_instability_threshold: float = 0.28

    guardrail_max_position_size: float = 0.12
    guardrail_max_sector_exposure: float = 0.35
    guardrail_max_daily_signal_volume: int = 25
    guardrail_extreme_volatility_threshold: float = 0.45

    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "alert_min_buy_probability",
        "alert_max_risk_score",
        "notification_default_min_probability",
        "notification_high_volatility_min_probability",
        "drift_min_accuracy",
        "drift_max_calibration_error",
        "drift_prediction_instability_threshold",
        "guardrail_max_position_size",
        "guardrail_max_sector_exposure",
        "guardrail_extreme_volatility_threshold",
    )
    @classmethod
    def _validate_probability(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("probability values must be between 0 and 1")
        return value

    @property
    def ticker_list(self) -> list[str]:
        return [ticker.strip().upper() for ticker in self.default_tickers.split(",") if ticker.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
