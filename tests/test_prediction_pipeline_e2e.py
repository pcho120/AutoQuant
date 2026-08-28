import numpy as np
import pandas as pd

from services.collection_config import CollectionConfig
from services.prediction_pipeline import PredictionPipeline


class MemoryPredictionRepository:
    def __init__(self, market_rows):
        self.market_rows = market_rows
        self.features = []
        self.evaluation = None
        self.artifact = None
        self.predictions = []

    def fetch_market_prices(self, tickers, timeframe="1d"):
        return [row for row in self.market_rows if row["ticker"] in tickers and row["timeframe"] == timeframe]

    def upsert_prediction_features(self, rows):
        keys = {(row["ticker"], row["timestamp"], row["feature_version"]): row for row in self.features}
        keys.update({(row["ticker"], row["timestamp"], row["feature_version"]): row for row in rows})
        self.features = list(keys.values())
        return len(rows)

    def fetch_prediction_features(self, feature_version):
        return [row for row in self.features if row["feature_version"] == feature_version]

    def upsert_model_evaluation(self, row):
        self.evaluation = row

    def upsert_model_artifact(self, row):
        self.artifact = row

    def fetch_latest_model_artifact(self, horizon):
        return self.artifact if self.artifact and self.artifact["horizon"] == horizon else None

    def upsert_predictions(self, rows):
        self.predictions = rows
        return len(rows)


def config() -> CollectionConfig:
    return CollectionConfig(
        tickers=("AAPL", "MSFT", "SPY", "QQQ", "^VIX", "XLK"),
        market_period="10y",
        market_interval="1d",
        news_lookback_days=2,
        retry_attempts=1,
        retry_base_delay_seconds=0,
        request_timeout_seconds=5,
        analysis_batch_size=10,
    )


def market_rows(days=700):
    dates = pd.bdate_range("2022-01-03", periods=days, tz="UTC")
    rows = []
    for ticker_index, ticker in enumerate(config().tickers):
        for index, timestamp in enumerate(dates):
            if ticker == "^VIX":
                close = 20 + 4 * np.sin(index / 17)
            else:
                close = 100 + ticker_index * 5 + index * 0.025 + 8 * np.sin(index / 9 + ticker_index)
            rows.append({
                "ticker": ticker,
                "timestamp": timestamp.isoformat(),
                "open": close - 0.3,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + (index % 25) * 20_000,
                "timeframe": "1d",
            })
    return rows


def test_market_to_features_to_model_to_cached_predictions():
    repository = MemoryPredictionRepository(market_rows())
    pipeline = PredictionPipeline(repository, config())

    feature_summary = pipeline.build_features()
    evaluation = pipeline.evaluate_model()
    prediction_summary = pipeline.run_predictions()

    assert feature_summary["tickers_succeeded"] == 4
    assert repository.features
    assert evaluation["status"] == "validated"
    assert repository.evaluation["brier_score"] >= 0
    assert repository.artifact["model_version"].startswith("prediction-v1.0.0-")
    assert prediction_summary == {"status": "validated", "predictions_upserted": 4}
    assert all(0 <= row["probability_up"] <= 1 for row in repository.predictions)
    assert all(row["model_version"].startswith("prediction-v1.0.0-") for row in repository.predictions)