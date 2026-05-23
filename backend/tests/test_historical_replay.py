from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from backend.historical_features.compute import compute_historical_features
from backend.historical_replay.context import ReplayDataset, StockSeries, _day_start
from backend.historical_replay.engine import ReplayConfig, run_replay
from backend.historical_replay.outcomes import evaluate_signal_outcome
from backend.historical_replay.regime import detect_regime_at
from backend.historical_replay.signals import generate_point_in_time_signal
from backend.historical_replay.service import create_replay_run

UTC = timezone.utc


def _price_rows(days: int, start_price: float = 100.0, start: date | None = None) -> list[dict]:
    rows = []
    base = datetime(2022, 1, 3, 21, tzinfo=UTC)
    price = start_price
    for index in range(days):
        price *= 1.001 if index % 4 else 0.999
        ts = base + timedelta(days=index)
        rows.append(
            {
                "timestamp": ts.isoformat(),
                "open": price * 0.99,
                "high": price * 1.01,
                "low": price * 0.98,
                "close": price,
                "volume": 1_000_000,
            }
        )
    return rows


def _build_series(stock_id: str, ticker: str, days: int, start_price: float) -> StockSeries:
    prices = _price_rows(days, start_price=start_price)
    features = compute_historical_features(prices, benchmark_rows=prices)
    price_frame = pd.DataFrame(prices)
    price_frame["timestamp"] = pd.to_datetime(price_frame["timestamp"], utc=True)
    feature_frame = features.copy()
    return StockSeries(
        stock_id=stock_id,
        ticker=ticker,
        prices=price_frame.sort_values("timestamp").reset_index(drop=True),
        features=feature_frame,
    )


def test_slice_before_excludes_replay_day_and_future() -> None:
    series = _build_series("stock-spy", "SPY", 120, 400.0)
    as_of = _day_start(date(2022, 3, 15))
    prices, features = series.slice_before(as_of)
    assert prices["timestamp"].max() < as_of
    assert features["timestamp"].max() < as_of


def test_signal_uses_only_past_rows() -> None:
    series = _build_series("stock-aapl", "AAPL", 120, 150.0)
    as_of = _day_start(date(2022, 4, 1))
    prices, features = series.slice_before(as_of)
    regime = detect_regime_at(series.prices[series.prices["timestamp"] < as_of])
    signal = generate_point_in_time_signal(
        stock_id="stock-aapl",
        prices=prices,
        features=features,
        regime=regime,
        signal_timestamp=prices.iloc[-1]["timestamp"].isoformat(),
    )
    assert signal is not None
    assert signal["signal_type"] in {"buy", "sell", "neutral"}
    assert 0 <= signal["probability"] <= 1


def test_outcome_uses_future_prices_not_in_signal_slice() -> None:
    series = _build_series("stock-aapl", "AAPL", 120, 150.0)
    as_of = _day_start(date(2022, 3, 1))
    prices, features = series.slice_before(as_of)
    regime = detect_regime_at(series.prices[series.prices["timestamp"] < as_of])
    signal = generate_point_in_time_signal(
        stock_id="stock-aapl",
        prices=prices,
        features=features,
        regime=regime,
        signal_timestamp=prices.iloc[-1]["timestamp"].isoformat(),
    )
    assert signal is not None
    signal["signal_type"] = "buy"
    outcome = evaluate_signal_outcome(signal, series)
    assert outcome is not None
    assert outcome["entry_timestamp"] > signal["timestamp"]


class FakeReplayRepository:
    def __init__(self, dataset: ReplayDataset, run: dict) -> None:
        self.dataset = dataset
        self.run = run
        self.signals: list[dict] = []
        self.outcomes: list[dict] = []
        self.snapshots: list[dict] = []

    def get_replay_run(self, replay_run_id: str) -> dict | None:
        return self.run if self.run["id"] == replay_run_id else None

    def update_replay_run(self, replay_run_id: str, **fields) -> dict:
        self.run.update(fields)
        return self.run

    def get_prices_in_range(self, stock_id: str, **kwargs) -> list[dict]:
        series = self.dataset.stocks.get(stock_id)
        if not series:
            return []
        return series.prices.to_dict(orient="records")

    def get_historical_features(self, stock_id: str, **kwargs) -> list[dict]:
        series = self.dataset.stocks.get(stock_id)
        if not series:
            return []
        return series.features.to_dict(orient="records")

    def insert_historical_signals(self, signals: list[dict]) -> list[dict]:
        stored = []
        for index, signal in enumerate(signals):
            row = {**signal, "id": f"signal-{len(self.signals) + index}"}
            self.signals.append(row)
            stored.append(row)
        return stored

    def insert_replay_outcome(self, **kwargs) -> dict:
        self.outcomes.append(kwargs)
        return kwargs

    def insert_replay_portfolio_snapshot(self, **kwargs) -> dict:
        self.snapshots.append(kwargs)
        return kwargs


def _trending_price_rows(days: int, start_price: float, daily_drift: float) -> list[dict]:
    rows = []
    base = datetime(2022, 1, 3, 21, tzinfo=UTC)
    price = start_price
    for index in range(days):
        price *= 1 + daily_drift
        ts = base + timedelta(days=index)
        rows.append(
            {
                "timestamp": ts.isoformat(),
                "open": price * 0.995,
                "high": price * 1.02,
                "low": price * 0.99,
                "close": price,
                "volume": 2_000_000 + index * 1000,
            }
        )
    return rows


def _build_trending_series(stock_id: str, ticker: str, days: int, start_price: float) -> StockSeries:
    prices = _trending_price_rows(days, start_price, daily_drift=0.008)
    features = compute_historical_features(prices, benchmark_rows=prices)
    price_frame = pd.DataFrame(prices)
    price_frame["timestamp"] = pd.to_datetime(price_frame["timestamp"], utc=True)
    return StockSeries(
        stock_id=stock_id,
        ticker=ticker,
        prices=price_frame.sort_values("timestamp").reset_index(drop=True),
        features=features,
    )


def test_run_replay_generates_signals_and_outcomes(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = _build_trending_series("stock-spy", "SPY", 200, 400.0)
    aapl = _build_trending_series("stock-aapl", "AAPL", 200, 150.0)
    dataset = ReplayDataset(
        benchmark_ticker="SPY",
        stocks={"stock-spy": spy, "stock-aapl": aapl},
        trading_days=[_to_date(ts) for ts in spy.prices["timestamp"].tolist()[60:80]],
        _benchmark_prices=spy.prices,
    )

    run = {
        "id": "run-1",
        "universe_name": "high_liquidity",
        "mode": "signal_only",
        "start_date": "2022-03-01",
        "end_date": "2022-04-30",
        "config": {"max_stocks": 2, "checkpoint_every_days": 1},
        "meta_model_version": "replay_v1",
        "signals_generated": 0,
        "outcomes_evaluated": 0,
    }
    repo = FakeReplayRepository(dataset, run)

    def fake_members(universe_slug, repository=None):
        return [
            {"stocks": {"id": "stock-spy", "ticker": "SPY"}},
            {"stocks": {"id": "stock-aapl", "ticker": "AAPL"}},
        ]

    monkeypatch.setattr("backend.historical_replay.engine.list_universe_members", fake_members)
    monkeypatch.setattr(
        "backend.historical_replay.engine.ReplayDataset.load",
        lambda *args, **kwargs: dataset,
    )

    def fake_evaluate(signal, series, **kwargs):
        enriched = {**signal, "signal_type": "buy"}
        return evaluate_signal_outcome(enriched, series, **kwargs)

    monkeypatch.setattr("backend.historical_replay.engine.evaluate_signal_outcome", fake_evaluate)

    result = run_replay("run-1", repository=repo, resume=False)
    assert result["status"] == "completed"
    assert len(repo.signals) > 0
    assert len(repo.outcomes) > 0



def _to_date(value) -> date:
    return pd.to_datetime(value, utc=True).date()


def test_create_replay_run_config() -> None:
    class Repo:
        def create_replay_run(self, **kwargs):
            return {"id": "run-x", **kwargs}

    run = create_replay_run("etf_only", years=1, max_stocks=5, repository=Repo())
    assert run["universe_name"] == "etf_only"
    assert run["mode"] == "signal_only"
