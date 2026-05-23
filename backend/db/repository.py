from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from backend.db.supabase_client import get_supabase_client
from backend.reliability.retry import RetryPolicy, retry_sync


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

    @staticmethod
    def _write_with_retry(operation: Any) -> Any:
        return retry_sync(
            operation,
            policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.2, max_delay_seconds=2.0),
        )

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

    def list_recent_indicators(self, limit: int = 1000) -> list[dict[str, Any]]:
        response = (
            self.client.table("technical_indicators")
            .select("*")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

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
        response = self._write_with_retry(
            lambda: (
                self.client.table("prediction_outcomes")
                .upsert(outcomes, on_conflict="prediction_id,horizon_days")
                .execute()
            )
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

    def list_prediction_outcomes_between(
        self,
        start_timestamp: str,
        end_timestamp: str,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("prediction_outcomes")
            .select("*")
            .gte("timestamp", start_timestamp)
            .lt("timestamp", end_timestamp)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def upsert_model_performance(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("model_performance")
                .upsert(rows, on_conflict="model_name")
                .execute()
            )
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

    def insert_model_drift_events(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("model_drift_events").insert(rows).execute()
        )
        return self._data(response)

    def list_recent_model_drift_events(
        self,
        since_timestamp: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.client.table("model_drift_events").select("*")
        if since_timestamp:
            query = query.gte("created_at", since_timestamp)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return self._data(response)

    def upsert_calibrated_predictions(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("calibrated_predictions")
                .upsert(rows, on_conflict="prediction_id")
                .execute()
            )
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
        response = self._write_with_retry(
            lambda: (
                self.client.table("market_regimes")
                .upsert(row, on_conflict="timestamp")
                .execute()
            )
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
        response = self._write_with_retry(
            lambda: self.client.table("meta_model_training_runs").insert(row).execute()
        )
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
        response = self._write_with_retry(
            lambda: (
                self.client.table("ensemble_signals")
                .upsert(signals, on_conflict="stock_id,timestamp")
                .execute()
            )
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

    def list_signals_for_quality(
        self,
        cutoff_timestamp: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("ensemble_signals")
            .select("*")
            .lte("timestamp", cutoff_timestamp)
            .order("timestamp")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def count_signals_since(self, since_timestamp: str) -> int:
        response = (
            self.client.table("ensemble_signals")
            .select("id", count="exact")
            .gte("timestamp", since_timestamp)
            .execute()
        )
        return int(getattr(response, "count", 0) or len(self._data(response)))

    def upsert_live_signal_performance(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("live_signal_performance")
                .upsert(rows, on_conflict="signal_id,horizon_days")
                .execute()
            )
        )
        return self._data(response)

    def list_live_signal_performance(self, limit: int = 1000) -> list[dict[str, Any]]:
        response = (
            self.client.table("live_signal_performance")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def upsert_model_regime_performance(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("model_regime_performance")
                .upsert(rows, on_conflict="model_name,regime")
                .execute()
            )
        )
        return self._data(response)

    def list_model_regime_performance(self) -> list[dict[str, Any]]:
        response = (
            self.client.table("model_regime_performance")
            .select("*")
            .order("updated_at", desc=True)
            .execute()
        )
        return self._data(response)

    def insert_portfolio_allocations(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("portfolio_allocations").insert(rows).execute()
        )
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
        response = self._write_with_retry(
            lambda: self.client.table("backtest_results").insert(row).execute()
        )
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

    def count_alerts_for_user_since(
        self,
        user_id: str,
        alert_type: str,
        since_timestamp: str,
    ) -> int:
        response = (
            self.client.table("alerts")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("alert_type", alert_type)
            .gte("created_at", since_timestamp)
            .execute()
        )
        return int(getattr(response, "count", 0) or len(self._data(response)))

    def latest_alert_for_user_stock(
        self,
        user_id: str,
        stock_id: str,
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("alerts")
            .select("*")
            .eq("user_id", user_id)
            .eq("stock_id", stock_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

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

    def get_notification_metrics(self, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("notification_metrics")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def list_notification_metrics(self, limit: int = 1000) -> list[dict[str, Any]]:
        response = (
            self.client.table("notification_metrics")
            .select("*")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def increment_notification_metrics(
        self,
        user_id: str,
        sent: int = 0,
        opened: int = 0,
        ignored: int = 0,
    ) -> dict[str, Any] | None:
        current = self.get_notification_metrics(user_id) or {
            "user_id": user_id,
            "notifications_sent": 0,
            "opened": 0,
            "ignored": 0,
        }
        notifications_sent = int(current.get("notifications_sent") or 0) + max(sent, 0)
        opened_count = int(current.get("opened") or 0) + max(opened, 0)
        ignored_count = int(current.get("ignored") or 0) + max(ignored, 0)
        engagement_score = 0.0
        if notifications_sent > 0:
            engagement_score = max(
                0.0,
                min(1.0, (opened_count + 0.25) / (notifications_sent + ignored_count + 0.25)),
            )
        row = {
            "user_id": user_id,
            "notifications_sent": notifications_sent,
            "opened": opened_count,
            "ignored": ignored_count,
            "engagement_score": engagement_score,
        }
        response = self._write_with_retry(
            lambda: (
                self.client.table("notification_metrics")
                .upsert(row, on_conflict="user_id")
                .execute()
            )
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def create_alerts(self, alerts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        if not alerts:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("alerts")
                .upsert(alerts, on_conflict="user_id,stock_id,alert_type,source_signal_timestamp")
                .execute()
            )
        )
        return self._data(response)

    def list_recent_notification_events(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = self.client.table("notification_events").select("*")
        if status:
            query = query.eq("status", status)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return self._data(response)

    def insert_notification_dead_letters(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("notification_dead_letters").insert(rows).execute()
        )
        return self._data(response)

    def insert_signal_audit_logs(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("signal_audit_log").insert(rows).execute()
        )
        return self._data(response)

    def list_signal_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        response = (
            self.client.table("signal_audit_log")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
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

    def list_stock_universes(self) -> list[dict[str, Any]]:
        response = self.client.table("stock_universes").select("*").order("name").execute()
        return self._data(response)

    def get_stock_universe_by_name(self, name: str) -> dict[str, Any] | None:
        response = (
            self.client.table("stock_universes")
            .select("*")
            .eq("name", name.strip().lower())
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_stock_universe(self, name: str, description: str | None = None) -> dict[str, Any]:
        row = {
            "name": name.strip().lower(),
            "description": description,
        }
        response = self._write_with_retry(
            lambda: self.client.table("stock_universes").upsert(row, on_conflict="name").execute()
        )
        rows = self._data(response)
        if rows:
            return rows[0]
        existing = self.get_stock_universe_by_name(name)
        if existing:
            return existing
        raise RuntimeError(f"Failed to upsert stock universe '{name}'")

    def replace_universe_memberships(
        self,
        universe_id: str,
        stock_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        self._write_with_retry(
            lambda: (
                self.client.table("universe_memberships")
                .delete()
                .eq("universe_id", universe_id)
                .execute()
            )
        )
        rows = [
            {"universe_id": universe_id, "stock_id": stock_id}
            for stock_id in dict.fromkeys(stock_ids)
        ]
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("universe_memberships").insert(rows).execute()
        )
        return self._data(response)

    def list_universe_members(self, universe_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("universe_memberships")
            .select("added_at, stocks(*)")
            .eq("universe_id", universe_id)
            .order("added_at", desc=True)
            .execute()
        )
        return self._data(response)

    def list_universe_tickers(self, universe_name: str) -> list[str]:
        universe = self.get_stock_universe_by_name(universe_name)
        if not universe:
            return []
        members = self.list_universe_members(universe["id"])
        tickers: list[str] = []
        for member in members:
            stock = member.get("stocks") or {}
            ticker = stock.get("ticker")
            if ticker:
                tickers.append(str(ticker).upper())
        return sorted(tickers)

    def get_price_backfill_state(
        self,
        stock_id: str,
        *,
        resolution: str = "daily",
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("price_backfill_state")
            .select("*")
            .eq("stock_id", stock_id)
            .eq("resolution", resolution)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_price_backfill_state(
        self,
        *,
        stock_id: str,
        resolution: str = "daily",
        target_start_date: str,
        target_end_date: str,
        status: str,
        earliest_stored_date: str | None = None,
        latest_stored_date: str | None = None,
        last_backfilled_through: str | None = None,
        last_provider: str | None = None,
        bars_stored: int = 0,
        chunks_total: int = 0,
        chunks_completed: int = 0,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "stock_id": stock_id,
            "resolution": resolution,
            "target_start_date": target_start_date,
            "target_end_date": target_end_date,
            "status": status,
            "earliest_stored_date": earliest_stored_date,
            "latest_stored_date": latest_stored_date,
            "last_backfilled_through": last_backfilled_through,
            "last_provider": last_provider,
            "bars_stored": bars_stored,
            "chunks_total": chunks_total,
            "chunks_completed": chunks_completed,
            "last_error": last_error,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        response = self._write_with_retry(
            lambda: (
                self.client.table("price_backfill_state")
                .upsert(row, on_conflict="stock_id,resolution")
                .execute()
            )
        )
        rows = self._data(response)
        return rows[0] if rows else row

    def get_prices_in_range(
        self,
        stock_id: str,
        *,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
        limit: int = 50000,
    ) -> list[dict[str, Any]]:
        query = self.client.table("stock_prices").select("*").eq("stock_id", stock_id)
        if start_timestamp:
            query = query.gte("timestamp", start_timestamp)
        if end_timestamp:
            query = query.lte("timestamp", end_timestamp)
        response = query.order("timestamp").limit(limit).execute()
        return self._data(response)

    def count_prices(self, stock_id: str) -> int:
        response = (
            self.client.table("stock_prices")
            .select("id", count="exact")
            .eq("stock_id", stock_id)
            .execute()
        )
        count = getattr(response, "count", None)
        if count is not None:
            return int(count)
        return len(self._data(response))

    def upsert_historical_features(
        self,
        features: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not features:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("historical_features")
                .upsert(features, on_conflict="stock_id,timestamp")
                .execute()
            )
        )
        return self._data(response)

    def get_historical_features(
        self,
        stock_id: str,
        *,
        start_timestamp: str | None = None,
        end_timestamp: str | None = None,
        limit: int = 50_000,
    ) -> list[dict[str, Any]]:
        query = self.client.table("historical_features").select("*").eq("stock_id", stock_id)
        if start_timestamp:
            query = query.gte("timestamp", start_timestamp)
        if end_timestamp:
            query = query.lte("timestamp", end_timestamp)
        response = query.order("timestamp").limit(limit).execute()
        return self._data(response)

    def create_replay_run(
        self,
        *,
        universe_name: str,
        mode: str,
        start_date: str,
        end_date: str,
        meta_model_version: str = "replay_v1",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row = {
            "universe_name": universe_name,
            "mode": mode,
            "start_date": start_date,
            "end_date": end_date,
            "status": "pending",
            "meta_model_version": meta_model_version,
            "config": config or {},
            "updated_at": datetime.now(UTC).isoformat(),
        }
        response = self._write_with_retry(
            lambda: self.client.table("replay_runs").insert(row).execute()
        )
        rows = self._data(response)
        return rows[0] if rows else row

    def get_replay_run(self, replay_run_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("replay_runs")
            .select("*")
            .eq("id", replay_run_id)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def update_replay_run(self, replay_run_id: str, **fields: Any) -> dict[str, Any] | None:
        if not fields:
            return self.get_replay_run(replay_run_id)
        payload = {**fields, "updated_at": datetime.now(UTC).isoformat()}
        response = self._write_with_retry(
            lambda: (
                self.client.table("replay_runs")
                .update(payload)
                .eq("id", replay_run_id)
                .execute()
            )
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def insert_historical_signals(
        self,
        signals: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not signals:
            return []
        rows = [
            {
                "replay_run_id": signal["replay_run_id"],
                "stock_id": signal["stock_id"],
                "timestamp": signal["timestamp"],
                "signal_type": signal["signal_type"],
                "probability": signal["probability"],
                "expected_return": signal["expected_return"],
                "risk_score": signal["risk_score"],
                "hold_days": signal["hold_days"],
                "regime": signal["regime"],
                "meta_model_version": signal["meta_model_version"],
                "model_predictions": signal.get("model_predictions") or [],
            }
            for signal in signals
        ]
        response = self._write_with_retry(
            lambda: self.client.table("historical_signals").insert(rows).execute()
        )
        return self._data(response)

    def insert_replay_outcome(
        self,
        *,
        replay_run_id: str,
        historical_signal_id: str,
        stock_id: str,
        entry_timestamp: str,
        exit_timestamp: str,
        entry_price: float,
        exit_price: float,
        actual_return: float,
        horizon_days: int,
        outcome: str,
        pnl: float,
    ) -> dict[str, Any] | None:
        row = {
            "replay_run_id": replay_run_id,
            "historical_signal_id": historical_signal_id,
            "stock_id": stock_id,
            "entry_timestamp": entry_timestamp,
            "exit_timestamp": exit_timestamp,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "actual_return": actual_return,
            "horizon_days": horizon_days,
            "outcome": outcome,
            "pnl": pnl,
        }
        response = self._write_with_retry(
            lambda: self.client.table("replay_outcomes").insert(row).execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def insert_replay_portfolio_snapshot(
        self,
        *,
        replay_run_id: str,
        snapshot_date: str,
        cash: float,
        equity: float,
        positions: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        row = {
            "replay_run_id": replay_run_id,
            "snapshot_date": snapshot_date,
            "cash": cash,
            "equity": equity,
            "positions": positions,
        }
        response = self._write_with_retry(
            lambda: (
                self.client.table("replay_portfolio_snapshots")
                .upsert(row, on_conflict="replay_run_id,snapshot_date")
                .execute()
            )
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def list_replay_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        response = (
            self.client.table("replay_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def list_historical_signals(
        self,
        *,
        replay_run_id: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("historical_signals")
            .select("*")
            .eq("replay_run_id", replay_run_id)
            .order("timestamp")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def update_historical_signal(self, signal_id: str, **fields: Any) -> dict[str, Any] | None:
        if not fields:
            return None
        response = self._write_with_retry(
            lambda: (
                self.client.table("historical_signals")
                .update(fields)
                .eq("id", signal_id)
                .execute()
            )
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def list_replay_outcomes(
        self,
        *,
        replay_run_id: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("replay_outcomes")
            .select("*")
            .eq("replay_run_id", replay_run_id)
            .order("exit_timestamp")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def list_replay_portfolio_snapshots(
        self,
        *,
        replay_run_id: str,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("replay_portfolio_snapshots")
            .select("*")
            .eq("replay_run_id", replay_run_id)
            .order("snapshot_date")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def upsert_historical_calibration_snapshots(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("historical_calibration_snapshots")
                .upsert(rows, on_conflict="replay_run_id,model_name,as_of_date")
                .execute()
            )
        )
        return self._data(response)

    def list_historical_calibration_snapshots(
        self,
        *,
        replay_run_id: str,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("historical_calibration_snapshots")
            .select("*")
            .eq("replay_run_id", replay_run_id)
            .order("as_of_date")
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def upsert_historical_regime_periods(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("historical_regime_periods")
                .upsert(rows, on_conflict="replay_run_id,start_date,regime")
                .execute()
            )
        )
        return self._data(response)

    def list_historical_regime_periods(
        self,
        *,
        replay_run_id: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = self.client.table("historical_regime_periods").select("*")
        if replay_run_id:
            query = query.eq("replay_run_id", replay_run_id)
        response = query.order("start_date").limit(limit).execute()
        return self._data(response)

    def insert_bootstrap_training_run(
        self,
        *,
        replay_run_id: str,
        training_type: str,
        status: str,
        metrics: dict[str, Any],
        meta_model_version: str | None = None,
    ) -> dict[str, Any] | None:
        row = {
            "replay_run_id": replay_run_id,
            "training_type": training_type,
            "status": status,
            "metrics": metrics,
            "meta_model_version": meta_model_version,
        }
        response = self._write_with_retry(
            lambda: self.client.table("bootstrap_training_runs").insert(row).execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def insert_dashboard_metrics(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("dashboard_metrics").insert(rows).execute()
        )
        return self._data(response)

    def list_dashboard_metrics(
        self,
        *,
        metric_group: str | None = None,
        metric_key: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        query = self.client.table("dashboard_metrics").select("*")
        if metric_group:
            query = query.eq("metric_group", metric_group)
        if metric_key:
            query = query.eq("metric_key", metric_key)
        response = query.order("recorded_at", desc=True).limit(limit).execute()
        return self._data(response)

    def upsert_drift_visualizations(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("drift_visualizations").insert(rows).execute()
        )
        return self._data(response)

    def list_drift_visualizations(
        self,
        *,
        model_name: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = self.client.table("drift_visualizations").select("*")
        if model_name:
            query = query.eq("model_name", model_name)
        response = query.order("snapshot_at", desc=True).limit(limit).execute()
        return self._data(response)

    def upsert_replay_snapshots(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("replay_snapshots")
                .upsert(rows, on_conflict="replay_run_id,snapshot_date")
                .execute()
            )
        )
        return self._data(response)

    def list_replay_snapshots(
        self,
        *,
        replay_run_id: str | None = None,
        snapshot_date: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = self.client.table("replay_snapshots").select("*")
        if replay_run_id:
            query = query.eq("replay_run_id", replay_run_id)
        if snapshot_date:
            query = query.eq("snapshot_date", snapshot_date)
        response = query.order("snapshot_date", desc=True).limit(limit).execute()
        return self._data(response)

    def get_replay_snapshot_at_date(
        self,
        replay_run_id: str,
        snapshot_date: str,
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("replay_snapshots")
            .select("*")
            .eq("replay_run_id", replay_run_id)
            .eq("snapshot_date", snapshot_date)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None

    def upsert_notification_engagement(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: (
                self.client.table("notification_engagement")
                .upsert(rows, on_conflict="user_id,period_start,period_end")
                .execute()
            )
        )
        return self._data(response)

    def list_notification_engagement(
        self,
        *,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("notification_engagement")
            .select("*")
            .order("period_end", desc=True)
            .limit(limit)
            .execute()
        )
        return self._data(response)

    def insert_infra_metrics(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        response = self._write_with_retry(
            lambda: self.client.table("infra_metrics").insert(rows).execute()
        )
        return self._data(response)

    def list_infra_metrics(
        self,
        *,
        component: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = self.client.table("infra_metrics").select("*")
        if component:
            query = query.eq("component", component)
        response = query.order("recorded_at", desc=True).limit(limit).execute()
        return self._data(response)

    def get_signal_audit_log(self, audit_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("signal_audit_log")
            .select("*, stocks(ticker, company_name, sector)")
            .eq("id", audit_id)
            .limit(1)
            .execute()
        )
        rows = self._data(response)
        return rows[0] if rows else None
