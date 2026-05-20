from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from backend.db.supabase_client import get_supabase_client


class SupabaseRepository:
    """Thin persistence boundary around Supabase tables.

    Algorithm modules depend on this repository shape instead of directly calling Supabase,
    which keeps the trading logic fast to unit test and easy to replace in batch jobs.
    """

    def __init__(self, client: Any | None = None):
        self.client = client or get_supabase_client()

    @staticmethod
    def _data(response: Any) -> list[dict[str, Any]]:
        data = getattr(response, "data", None)
        if data is None:
            return []
        return data if isinstance(data, list) else [data]

    def list_stocks(self) -> list[dict[str, Any]]:
        response = self.client.table("stocks").select("*").order("ticker").execute()
        return self._data(response)

    def get_stock_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        response = (
            self.client.table("stocks")
            .select("*")
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def get_stock(self, stock_id: str) -> dict[str, Any] | None:
        response = self.client.table("stocks").select("*").eq("id", stock_id).limit(1).execute()
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_stocks(self, stocks: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = [
            {
                **stock,
                "ticker": str(stock["ticker"]).upper(),
                "company_name": stock.get("company_name") or stock["ticker"],
            }
            for stock in stocks
        ]
        if not rows:
            return []
        response = self.client.table("stocks").upsert(rows, on_conflict="ticker").execute()
        return self._data(response)

    def upsert_prices(self, prices: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not prices:
            return []
        response = (
            self.client.table("stock_prices")
            .upsert(prices, on_conflict="stock_id,timestamp")
            .execute()
        )
        return self._data(response)

    def get_prices(self, stock_id: str, limit: int = 300) -> list[dict[str, Any]]:
        response = (
            self.client.table("stock_prices")
            .select("*")
            .eq("stock_id", stock_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(self._data(response)))

    def get_prices_for_ticker(self, ticker: str, limit: int = 300) -> list[dict[str, Any]]:
        stock = self.get_stock_by_ticker(ticker)
        if not stock:
            return []
        return self.get_prices(stock["id"], limit=limit)

    def get_price_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        response = (
            self.client.table("stock_prices")
            .select("*")
            .eq("stock_id", stock_id)
            .lte("timestamp", timestamp)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def get_price_at_or_after(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        response = (
            self.client.table("stock_prices")
            .select("*")
            .eq("stock_id", stock_id)
            .gte("timestamp", timestamp)
            .order("timestamp")
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_indicators(self, indicators: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not indicators:
            return []
        response = (
            self.client.table("technical_indicators")
            .upsert(indicators, on_conflict="stock_id,timestamp")
            .execute()
        )
        return self._data(response)

    def get_indicators(self, stock_id: str, limit: int = 300) -> list[dict[str, Any]]:
        response = (
            self.client.table("technical_indicators")
            .select("*")
            .eq("stock_id", stock_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(self._data(response)))

    def get_indicator_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        response = (
            self.client.table("technical_indicators")
            .select("*")
            .eq("stock_id", stock_id)
            .lte("timestamp", timestamp)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_model_predictions(self, predictions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not predictions:
            return []
        response = (
            self.client.table("model_predictions")
            .upsert(predictions, on_conflict="stock_id,timestamp,model_name")
            .execute()
        )
        return self._data(response)

    def get_model_predictions(
        self,
        stock_id: str,
        timestamp: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        query = self.client.table("model_predictions").select("*").eq("stock_id", stock_id)
        if timestamp:
            query = query.eq("timestamp", timestamp)
        response = query.order("timestamp", desc=True).limit(limit).execute()
        return self._data(response)

    def list_model_predictions_for_feedback(
        self,
        cutoff_timestamp: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("model_predictions")
            .select("*")
            .lte("timestamp", cutoff_timestamp)
            .order("timestamp")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def list_recent_model_predictions(self, limit: int = 1000) -> list[dict[str, Any]]:
        response = (
            self.client.table("model_predictions")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def get_prediction_outcomes_for_prediction_ids(
        self,
        prediction_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        ids = list(prediction_ids)
        if not ids:
            return []
        response = (
            self.client.table("prediction_outcomes")
            .select("prediction_id,horizon_days")
            .in_("prediction_id", ids)
            .execute()
        )
        return self._data(response)

    def upsert_prediction_outcomes(
        self,
        outcomes: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not outcomes:
            return []
        response = (
            self.client.table("prediction_outcomes")
            .upsert(outcomes, on_conflict="prediction_id,horizon_days")
            .execute()
        )
        return self._data(response)

    def list_prediction_outcomes(
        self,
        since_timestamp: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        query = self.client.table("prediction_outcomes").select("*")
        if since_timestamp:
            query = query.gte("timestamp", since_timestamp)
        response = query.order("timestamp", desc=True).limit(limit).execute()
        return self._data(response)

    def upsert_model_performance(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = (
            self.client.table("model_performance")
            .upsert(rows, on_conflict="model_name")
            .execute()
        )
        return self._data(response)

    def list_model_performance(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("model_performance")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
        return self._data(response)

    def upsert_calibrated_predictions(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = (
            self.client.table("calibrated_predictions")
            .upsert(rows, on_conflict="prediction_id")
            .execute()
        )
        return self._data(response)

    def list_calibrated_predictions(
        self,
        stock_id: str | None = None,
        timestamp: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        query = self.client.table("calibrated_predictions").select("*")
        if stock_id:
            query = query.eq("stock_id", stock_id)
        if timestamp:
            query = query.eq("timestamp", timestamp)
        response = query.order("timestamp", desc=True).limit(limit).execute()
        return self._data(response)

    def latest_calibrated_prediction_timestamp(self) -> str | None:
        response = (
            self.client.table("calibrated_predictions")
            .select("timestamp")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return str(rows[0]["timestamp"]) if rows else None

    def upsert_market_regime(self, row: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            self.client.table("market_regimes")
            .upsert(row, on_conflict="timestamp")
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def latest_market_regime(self) -> dict[str, Any] | None:
        response = (
            self.client.table("market_regimes")
            .select("*")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def get_market_regime_at_or_before(self, timestamp: str) -> dict[str, Any] | None:
        response = (
            self.client.table("market_regimes")
            .select("*")
            .lte("timestamp", timestamp)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def insert_meta_model_training_run(self, row: dict[str, Any]) -> dict[str, Any] | None:
        response = self.client.table("meta_model_training_runs").insert(row).execute()
        rows = self._data(response)
        return rows[0] if rows else None

    def latest_meta_model_training_run(self) -> dict[str, Any] | None:
        response = (
            self.client.table("meta_model_training_runs")
            .select("*")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_ensemble_signals(self, signals: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not signals:
            return []
        response = (
            self.client.table("ensemble_signals")
            .upsert(signals, on_conflict="stock_id,timestamp")
            .execute()
        )
        return self._data(response)

    def list_signals(self, limit: int = 100) -> list[dict[str, Any]]:
        response = (
            self.client.table("ensemble_signals")
            .select("*, stocks(*)")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def list_signals_for_backtest(self, limit: int = 1000) -> list[dict[str, Any]]:
        response = (
            self.client.table("ensemble_signals")
            .select("*, stocks(*)")
            .order("timestamp")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def insert_portfolio_allocations(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self.client.table("portfolio_allocations").insert(rows).execute()
        return self._data(response)

    def list_latest_portfolio_allocations(self) -> list[dict[str, Any]]:
        latest_response = (
            self.client.table("portfolio_allocations")
            .select("run_id")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest = self._data(latest_response)
        if not latest:
            return []
        response = (
            self.client.table("portfolio_allocations")
            .select("*, stocks(*)")
            .eq("run_id", latest[0]["run_id"])
            .order("allocation", desc=True)
            .execute()
        )
        return self._data(response)

    def insert_backtest_result(self, row: dict[str, Any]) -> dict[str, Any] | None:
        response = self.client.table("backtest_results").insert(row).execute()
        rows = self._data(response)
        return rows[0] if rows else None

    def latest_backtest_result(self) -> dict[str, Any] | None:
        response = (
            self.client.table("backtest_results")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def get_signals_for_ticker(self, ticker: str, limit: int = 100) -> list[dict[str, Any]]:
        stock = self.get_stock_by_ticker(ticker)
        if not stock:
            return []
        response = (
            self.client.table("ensemble_signals")
            .select("*, stocks(*)")
            .eq("stock_id", stock["id"])
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def latest_signal_for_stock(self, stock_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("ensemble_signals")
            .select("*")
            .eq("stock_id", stock_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def list_watchlist(self, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("user_watchlists")
            .select("*, stocks(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return self._data(response)

    def add_watchlist_stock(self, user_id: str, stock_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("user_watchlists")
            .upsert({"user_id": user_id, "stock_id": stock_id}, on_conflict="user_id,stock_id")
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def list_portfolio(self, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("user_portfolio")
            .select("*, stocks(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return self._data(response)

    def list_alerts(self, user_id: str, unread_only: bool = False) -> list[dict[str, Any]]:
        query = (
            self.client.table("alerts")
            .select("*, stocks(*)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if unread_only:
            query = query.eq("is_read", False)
        response = query.execute()
        return self._data(response)

    def mark_alerts_read(self, user_id: str, alert_ids: Iterable[str]) -> list[dict[str, Any]]:
        ids = list(alert_ids)
        if not ids:
            return []
        response = (
            self.client.table("alerts")
            .update({"is_read": True})
            .eq("user_id", user_id)
            .in_("id", ids)
            .execute()
        )
        return self._data(response)

    def create_alerts(self, alerts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not alerts:
            return []
        response = (
            self.client.table("alerts")
            .upsert(alerts, on_conflict="user_id,stock_id,alert_type,source_signal_timestamp")
            .execute()
        )
        return self._data(response)

    def users_interested_in_stock(self, stock_id: str) -> list[str]:
        watchlist_response = (
            self.client.table("user_watchlists").select("user_id").eq("stock_id", stock_id).execute()
        )
        portfolio_response = (
            self.client.table("user_portfolio").select("user_id").eq("stock_id", stock_id).execute()
        )
        user_ids = {
            row["user_id"]
            for row in [*self._data(watchlist_response), *self._data(portfolio_response)]
            if row.get("user_id")
        }
        return sorted(user_ids)
