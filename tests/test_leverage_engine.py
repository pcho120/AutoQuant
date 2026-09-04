import numpy as np
import pandas as pd
import pytest

from services.leverage_engine import (
    BacktestConfig,
    LeverageBacktester,
    LeverageEngineService,
    TripodLeverageStrategy,
    generate_synthetic_leverage_data,
)


def history(close: np.ndarray | list[float], start: str = "2020-01-02") -> pd.DataFrame:
    values = np.asarray(close, dtype=float)
    index = pd.bdate_range(start, periods=len(values), tz="UTC")
    return pd.DataFrame({
        "Open": values * 0.999,
        "High": values * 1.005,
        "Low": values * 0.995,
        "Close": values,
        "Volume": 1_000_000,
    }, index=index)


def test_neutral_zone_keeps_previous_directional_state():
    prices = np.concatenate([np.full(250, 100.0), [102.0, 100.0, 90.0, 97.0]])
    vix = history(np.full(len(prices), 20.0))

    signals = TripodLeverageStrategy().calculate_signals(history(prices), vix)

    assert signals["state"].iloc[-4:].tolist() == ["BULL", "BULL", "BEAR", "BEAR"]


@pytest.mark.parametrize(
    ("trend", "vix_level", "expected"),
    [
        ("bull", 20.0, "TQQQ"),
        ("bull", 30.0, "QQQ_QLD"),
        ("bear", 15.0, "QQQ_QLD"),
        ("bear", 25.0, "CASH"),
    ],
)
def test_tripod_allocation_cases(trend, vix_level, expected):
    prices = np.linspace(100.0, 180.0, 300) if trend == "bull" else np.linspace(180.0, 100.0, 300)

    latest = TripodLeverageStrategy().latest_signal(
        history(prices), history(np.full(len(prices), vix_level)),
    )

    assert latest["allocation"] == expected
    assert sum(latest["weights"].values()) == pytest.approx(1.0)


def test_synthetic_leverage_uses_daily_reset_returns_and_expense():
    qqq = history([100.0, 110.0, 99.0])

    synthetic = generate_synthetic_leverage_data(
        qqq, leverage=2.0, annual_expense_ratio=0.0252, initial_price=100.0,
    )

    daily_fee = 0.0252 / 252
    assert synthetic["Close"].iloc[1] == pytest.approx(100.0 * (1.2 - daily_fee))
    assert synthetic["Close"].iloc[2] == pytest.approx(
        100.0 * (1.2 - daily_fee) * (0.8 - daily_fee),
    )


def test_backtest_executes_signal_on_next_trading_day_and_models_costs():
    days = 320
    qqq = history(100 + np.arange(days) * 0.15)
    vix = history(np.full(days, 20.0))
    strategy = TripodLeverageStrategy()
    signals = strategy.calculate_signals(qqq, vix).dropna(subset=["allocation"])
    backtester = LeverageBacktester(strategy)

    no_cost = backtester.run(
        qqq, vix, qqq,
        BacktestConfig(commission_rate=0.0, slippage_rate=0.0, execution_price="close"),
    )
    with_cost = backtester.run(
        qqq, vix, qqq,
        BacktestConfig(commission_rate=0.001, slippage_rate=0.001, execution_price="close"),
    )

    first_trade = with_cost.trades[0]
    first_signal_position = qqq.index.get_loc(pd.Timestamp(first_trade["signal_date"]))
    first_execution_position = qqq.index.get_loc(pd.Timestamp(first_trade["execution_date"]))
    assert first_execution_position == first_signal_position + 1
    assert pd.Timestamp(first_trade["signal_date"]) == signals.index[0]
    assert with_cost.metrics.total_rebalances == len(with_cost.trades)
    assert with_cost.equity_curve[-1]["equity"] < no_cost.equity_curve[-1]["equity"]
    assert with_cost.metrics.mdd <= 0


def test_service_uses_selected_index_as_long_history_leverage_proxy():
    class FakeMarket:
        def __init__(self):
            self.requested = []

        def fetch_historical_data(self, ticker, period, interval):
            self.requested.append((ticker, period, interval))
            values = np.linspace(100.0, 180.0, 320) if ticker == "^NDX" else np.full(320, 20.0)
            return history(values)

    market = FakeMarket()

    result = LeverageEngineService(market).run_backtest("^NDX", "max")

    assert result["one_x_proxy"] == "^NDX"
    assert {request[0] for request in market.requested} == {"^NDX", "^VIX"}