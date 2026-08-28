import numpy as np
import pandas as pd

from services.ml_pipeline import (
    MODEL_FEATURES,
    WalkForwardTrainer,
    expanding_purged_splits,
    prepare_training_dataset,
)


def synthetic_dataset(days: int = 520, tickers: tuple[str, ...] = ("AAPL", "MSFT", "NVDA", "SPY")) -> pd.DataFrame:
    dates = pd.bdate_range("2022-01-03", periods=days, tz="UTC")
    rows = []
    for ticker_index, ticker in enumerate(tickers):
        for index, timestamp in enumerate(dates):
            momentum = np.sin(index / 12 + ticker_index) * 0.02
            row = {feature: momentum + (feature_index * 0.0001) for feature_index, feature in enumerate(MODEL_FEATURES)}
            row.update({
                "ticker": ticker,
                "timestamp": timestamp,
                "future_return": momentum + np.sin(index / 3) * 0.005,
                "direction_up": int(momentum + np.sin(index / 3) * 0.005 > 0),
            })
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["timestamp", "ticker"]).reset_index(drop=True)


def test_target_generation_uses_exactly_future_five_trading_rows():
    dates = pd.bdate_range("2026-01-01", periods=12, tz="UTC")
    prices = pd.DataFrame({"ticker": "AAPL", "timestamp": dates, "close": np.arange(100.0, 112.0)})
    features = pd.DataFrame({"ticker": "AAPL", "timestamp": dates, "rsi_14": 50.0})

    dataset = prepare_training_dataset(features, prices, horizon_days=5)

    assert len(dataset) == 7
    assert dataset.iloc[0]["future_return"] == 105 / 100 - 1
    assert "future_return" not in features.columns


def test_expanding_split_has_horizon_purge_gaps():
    data = synthetic_dataset()
    split = expanding_purged_splits(data["timestamp"])[0]
    train_end = data.iloc[split.train]["timestamp"].max()
    validation_start = data.iloc[split.validation]["timestamp"].min()
    validation_end = data.iloc[split.validation]["timestamp"].max()
    test_start = data.iloc[split.test]["timestamp"].min()

    assert len(pd.bdate_range(train_end, validation_start)) - 1 > 5
    assert len(pd.bdate_range(validation_end, test_start)) - 1 > 5


def test_walk_forward_outputs_calibrated_probabilities_and_metrics():
    result = WalkForwardTrainer().evaluate(synthetic_dataset())

    assert result.status == "validated"
    assert result.model is not None
    assert result.model.calibration_method in {"sigmoid", "isotonic"}
    assert result.out_of_sample["probability_up"].between(0, 1).all()
    assert {"auc", "brier_score", "log_loss", "directional_accuracy", "mae", "rmse"} <= result.metrics.keys()


def test_short_history_returns_honest_insufficient_status():
    result = WalkForwardTrainer().evaluate(synthetic_dataset(200))

    assert result.status == "insufficient_historical_validation_data"
    assert result.model is None
    assert result.metrics == {}