from __future__ import annotations

import asyncio
from datetime import date

import httpx

from backend.core.config import Settings, get_settings
from backend.data_pipeline.providers import MarketDataProvider, PriceBar, configured_providers
from backend.reliability.retry import RetryPolicy


class ProviderFetchError(RuntimeError):
    def __init__(self, provider: str, message: str, *, retryable: bool = True):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.retryable = retryable


def _is_rate_limited(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    message = str(exc).lower()
    return "rate limit" in message or "too many requests" in message or "api call frequency" in message


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ProviderFetchError):
        return exc.retryable
    if isinstance(exc, httpx.HTTPError):
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return status is None or status >= 500 or status == 429
    return True


async def fetch_prices_with_failover(
    ticker: str,
    start_date: date,
    end_date: date,
    *,
    settings: Settings | None = None,
    providers: list[MarketDataProvider] | None = None,
    retry_policy: RetryPolicy | None = None,
    provider_cooldown_seconds: float = 0.0,
) -> tuple[list[PriceBar], str | None]:
    """Fetch real OHLCV bars using provider failover (Polygon → Finnhub → Alpha Vantage)."""
    settings = settings or get_settings()
    provider_list = providers or configured_providers(settings)
    if not provider_list:
        raise ProviderFetchError("none", "no market data providers configured", retryable=False)

    policy = retry_policy or RetryPolicy(max_attempts=3, base_delay_seconds=0.5, max_delay_seconds=8.0)
    errors: list[str] = []

    for provider in provider_list:
        for attempt in range(1, policy.max_attempts + 1):
            try:
                bars = await provider.fetch_historical_prices(ticker, start_date, end_date)
                if bars:
                    return bars, provider.name
                errors.append(f"{provider.name}: empty response")
                break
            except Exception as exc:
                retryable = _is_retryable(exc)
                errors.append(f"{provider.name}: {exc}")
                if not retryable or attempt >= policy.max_attempts:
                    break
                delay = policy.delay_for_attempt(attempt)
                if _is_rate_limited(exc):
                    delay = max(delay, 2.0)
                await asyncio.sleep(delay)
        if provider_cooldown_seconds > 0:
            await asyncio.sleep(provider_cooldown_seconds)

    raise ProviderFetchError("all", "; ".join(errors), retryable=False)
