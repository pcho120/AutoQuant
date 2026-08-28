import numpy as np
import pandas as pd

from services.feature_engine import FEATURE_VERSION, FeatureEngine


def prices(length: int = 260, offset: float = 0.0) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=length, tz="UTC")
    close = 100 + offset + np.linspace(0, 30, length) + np.sin(np.arange(length) / 5)
    return pd.DataFrame({
        "open": close - 0.3,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": 1_000_000 + (np.arange(length) % 20) * 10_000,
    }, index=index)


def test_feature_engine_calculates_complete_latest_snapshot():
    source = prices()
    result = FeatureEngine().build("AAPL", source, prices(offset=20), prices(offset=30), prices(offset=-80), prices(offset=10), "XLK")

    assert result.skipped_reason is None
    assert result.rows
    latest = result.rows[-1]
    assert latest["feature_version"] == FEATURE_VERSION
    assert latest["ticker"] == "AAPL"
    assert 0 <= latest["rsi_14"] <= 100
    assert latest["atr_14"] > 0
    assert latest["sma_200"] > 0
    assert latest["market_trend"] == "bullish"


def test_feature_engine_requires_sufficient_history():
    short = prices(80)
    result = FeatureEngine().build("AAPL", short, short, short, short)

    assert result.rows == []
    assert result.skipped_reason == "requires at least 200 daily candles"


def test_appending_future_data_does_not_change_past_features():
    source = prices(250)
    engine = FeatureEngine()
    original = engine.build("AAPL", source, source, source, prices(250, -80)).rows
    future = prices(260).iloc[250:].copy()
    extended = pd.concat([source, future])
    vix_source = prices(250, -80)
    extended_vix = pd.concat([vix_source, prices(260, -80).iloc[250:]])
    rebuilt = engine.build("AAPL", extended, extended, extended, extended_vix).rows

    original_by_time = {row["timestamp"]: row for row in original}
    rebuilt_by_time = {row["timestamp"]: row for row in rebuilt}
    shared_timestamp = original[-1]["timestamp"]
    assert rebuilt_by_time[shared_timestamp] == original_by_time[shared_timestamp]


def test_future_benchmark_value_is_never_backfilled():
    source = prices(260)
    benchmark = prices(260)
    benchmark = benchmark.iloc[220:].copy()
    result = FeatureEngine().build("AAPL", source, benchmark, benchmark, benchmark)

    assert result.rows
    assert min(pd.Timestamp(row["timestamp"]) for row in result.rows) >= benchmark.index[20]