from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

import numpy as np
import pandas as pd

from adapters.collection_repository import CollectionRepository
from services.collection_config import CollectionConfig
from services.feature_engine import FEATURE_VERSION, SECTOR_ETFS, FeatureEngine
from services.ml_pipeline import (
    MODEL_FEATURES,
    MODEL_VERSION,
    TrainedModel,
    WalkForwardTrainer,
    expanding_purged_splits,
    prepare_training_dataset,
)
from services.retry import retry_call


logger = logging.getLogger(__name__)


def _frames_by_ticker(rows: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    if not rows:
        return {}
    data = pd.DataFrame(rows)
    data["ticker"] = data["ticker"].astype(str).str.upper()
    return {
        ticker: group.drop(columns=["ticker"]).sort_values("timestamp").reset_index(drop=True)
        for ticker, group in data.groupby("ticker")
    }


class PredictionPipeline:
    def __init__(self, repository: CollectionRepository, config: CollectionConfig):
        self.repository = repository
        self.config = config

    def build_features(self) -> dict[str, int]:
        market_rows = self.repository.fetch_market_prices(self.config.tickers, timeframe="1d")
        frames = _frames_by_ticker(market_rows)
        summary = {"tickers_succeeded": 0, "tickers_skipped": 0, "tickers_failed": 0, "rows_upserted": 0}
        benchmarks = {symbol: frames.get(symbol) for symbol in ("SPY", "QQQ", "^VIX")}
        if any(frame is None for frame in benchmarks.values()):
            raise ValueError("SPY, QQQ, and ^VIX daily history are required to build features")

        prediction_tickers = [ticker for ticker in self.config.tickers if ticker not in {"^VIX", *set(SECTOR_ETFS.values())}]
        engine = FeatureEngine()
        for ticker in prediction_tickers:
            try:
                prices = frames.get(ticker)
                if prices is None:
                    summary["tickers_skipped"] += 1
                    continue
                sector_etf = SECTOR_ETFS.get(ticker)
                result = engine.build(
                    ticker,
                    prices,
                    benchmarks["SPY"],
                    benchmarks["QQQ"],
                    benchmarks["^VIX"],
                    frames.get(sector_etf) if sector_etf else None,
                    sector_etf,
                )
                if result.skipped_reason or not result.rows:
                    summary["tickers_skipped"] += 1
                    logger.warning("Feature build skipped for %s: %s", ticker, result.skipped_reason or "no complete rows")
                    continue
                for start in range(0, len(result.rows), 500):
                    batch = result.rows[start:start + 500]
                    summary["rows_upserted"] += retry_call(
                        lambda batch=batch: self.repository.upsert_prediction_features(batch),
                        attempts=self.config.retry_attempts,
                        base_delay_seconds=self.config.retry_base_delay_seconds,
                    )
                summary["tickers_succeeded"] += 1
            except Exception:
                summary["tickers_failed"] += 1
                logger.exception("Feature build failed for %s", ticker)
        return summary

    def evaluate_model(self) -> dict[str, Any]:
        feature_rows = self.repository.fetch_prediction_features(FEATURE_VERSION)
        market_rows = self.repository.fetch_market_prices(self.config.tickers, timeframe="1d")
        if not feature_rows or not market_rows:
            return {"status": "insufficient_historical_validation_data"}
        features = pd.DataFrame(feature_rows)
        prices = pd.DataFrame(market_rows)
        dataset = prepare_training_dataset(features, prices, horizon_days=5)
        trainer = WalkForwardTrainer(horizon_days=5)
        evaluation = trainer.evaluate(dataset)
        if evaluation.status != "validated" or evaluation.model is None:
            return {"status": evaluation.status, "samples": len(dataset)}

        latest_model = trainer.fit_latest(dataset)
        if latest_model is None:
            return {"status": "insufficient_historical_validation_data", "samples": len(dataset)}
        latest_model.evaluation_metrics = evaluation.metrics.copy()
        residuals = evaluation.out_of_sample["future_return"] - evaluation.out_of_sample["expected_return"]
        latest_model.residual_downside_quantile = float(residuals.quantile(0.1))
        trained_at = datetime.now(timezone.utc)
        now = trained_at.isoformat()
        model_version = f"{MODEL_VERSION}-{trained_at.strftime('%Y%m%dT%H%M%SZ')}"
        latest_model.model_version = model_version
        oos = evaluation.out_of_sample
        first_split = expanding_purged_splits(dataset["timestamp"], horizon_days=5)[0]
        first_train = dataset.iloc[first_split.train]
        first_validation = dataset.iloc[first_split.validation]
        evaluation_row = {
            "model_version": model_version,
            "feature_version": FEATURE_VERSION,
            "horizon": "5d",
            "train_start": pd.to_datetime(first_train["timestamp"], utc=True).min().isoformat(),
            "train_end": pd.to_datetime(first_train["timestamp"], utc=True).max().isoformat(),
            "validation_start": pd.to_datetime(first_validation["timestamp"], utc=True).min().isoformat(),
            "validation_end": pd.to_datetime(first_validation["timestamp"], utc=True).max().isoformat(),
            "test_start": pd.to_datetime(oos["timestamp"], utc=True).min().isoformat(),
            "test_end": pd.to_datetime(oos["timestamp"], utc=True).max().isoformat(),
            **{key: value for key, value in evaluation.metrics.items() if key not in {"classifier_name", "regressor_name", "reliability"}},
            "calibration_method": latest_model.calibration_method,
            "evaluation_details": {
                "validation": "expanding_walk_forward_with_5_trading_day_purge",
                "classifier_selected": latest_model.classifier_name,
                "regressor_selected": latest_model.regressor_name,
                "reliability": evaluation.metrics.get("reliability"),
                "news_features_used": False,
                "fold_count": int(oos["fold"].nunique()),
            },
        }
        self.repository.upsert_model_evaluation(evaluation_row)
        self.repository.upsert_model_artifact({
            "model_version": model_version,
            "feature_version": FEATURE_VERSION,
            "horizon": "5d",
            "classifier_name": latest_model.classifier_name,
            "regressor_name": latest_model.regressor_name,
            "calibration_method": latest_model.calibration_method,
            "artifact_base64": latest_model.serialize(),
            "training_metadata": evaluation.metrics,
            "trained_at": now,
        })
        return {"status": "validated", "samples": len(dataset), **evaluation.metrics}

    def run_predictions(self) -> dict[str, int | str]:
        artifact_row = self.repository.fetch_latest_model_artifact("5d")
        if not artifact_row:
            return {"status": "insufficient_historical_validation_data", "predictions_upserted": 0}
        model = TrainedModel.deserialize(artifact_row["artifact_base64"])
        features = pd.DataFrame(self.repository.fetch_prediction_features(FEATURE_VERSION))
        prices = pd.DataFrame(self.repository.fetch_market_prices(self.config.tickers, timeframe="1d"))
        if features.empty or prices.empty:
            return {"status": "insufficient_historical_validation_data", "predictions_upserted": 0}
        features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True)
        prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True)
        latest = features.sort_values("timestamp").groupby("ticker", as_index=False).tail(1)
        latest_prices = prices.sort_values("timestamp").groupby("ticker", as_index=False).tail(1)
        latest = latest.merge(
            latest_prices[["ticker", "timestamp", "close"]], on=["ticker", "timestamp"], how="inner",
        )
        if latest.empty:
            return {"status": "insufficient_historical_validation_data", "predictions_upserted": 0}

        probabilities = model.classifier.predict_proba(latest[MODEL_FEATURES])[:, 1]
        expected_returns = model.regressor.predict(latest[MODEL_FEATURES])
        reliability = float((model.evaluation_metrics or {}).get("reliability") or 0.0)
        rows = []
        for (_, feature), probability, expected_return in zip(latest.iterrows(), probabilities, expected_returns):
            current_price = float(feature["close"])
            downside_return = float(expected_return + model.residual_downside_quantile)
            downside_risk = max(0.0, -downside_return)
            risk_reward = float(expected_return / downside_risk) if downside_risk > 0 else None
            signal = "BUY" if probability > 0.5 and expected_return > 0 else "SELL" if probability < 0.5 and expected_return < 0 else "HOLD"
            rows.append({
                "ticker": feature["ticker"],
                "prediction_timestamp": feature["timestamp"].isoformat(),
                "horizon": "5d",
                "current_price": current_price,
                "expected_return": float(expected_return),
                "predicted_price": current_price * (1 + float(expected_return)),
                "probability_up": float(probability),
                "downside_risk": downside_risk,
                "risk_reward": risk_reward,
                "signal": signal,
                "reliability": reliability,
                "reliability_status": "validated",
                "model_version": model.model_version,
                "feature_version": FEATURE_VERSION,
                "explanation": self._explain(feature),
            })
        self.repository.upsert_predictions(rows)
        return {"status": "validated", "predictions_upserted": len(rows)}

    @staticmethod
    def _explain(feature: pd.Series) -> dict[str, Any]:
        bullish = []
        risks = []
        if feature["return_20d"] > 0:
            bullish.append("Positive 20-day price momentum")
        else:
            risks.append("Negative 20-day price momentum")
        if feature["macd_histogram"] > 0:
            bullish.append("MACD momentum is positive")
        else:
            risks.append("MACD momentum is negative")
        if feature["relative_volume"] > 1:
            bullish.append("Trading volume is above its 20-day average")
        if feature["rsi_14"] >= 70:
            risks.append("RSI is in an overbought range")
        if feature["atr_pct"] > 0.04:
            risks.append("Daily ATR indicates elevated volatility")
        if feature["market_trend"] == "bearish":
            risks.append("SPY and QQQ 20-day regimes are negative")
        return {
            "bullish_factors": bullish,
            "risk_factors": risks,
            "technical": {key: _json_number(feature.get(key)) for key in ("rsi_14", "macd", "macd_signal", "atr_pct", "relative_volume")},
            "market_regime": {
                "spy_return_20d": _json_number(feature.get("spy_return_20d")),
                "qqq_return_20d": _json_number(feature.get("qqq_return_20d")),
                "vix": _json_number(feature.get("vix")),
                "sector_etf": feature.get("sector_etf"),
                "sector_return_20d": _json_number(feature.get("sector_return_20d")),
            },
        }


def _json_number(value: Any) -> float | None:
    return float(value) if value is not None and not pd.isna(value) and np.isfinite(float(value)) else None