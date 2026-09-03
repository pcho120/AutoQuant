from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import base64
import math

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


MODEL_VERSION = "prediction-v1.0.0"
PRIMARY_HORIZON = 5
MIN_TRAIN_DAYS = 252
CALIBRATION_DAYS = 63
TEST_DAYS = 63
MIN_CALIBRATION_SAMPLES = 200

MODEL_FEATURES = [
    "rsi_14", "macd_histogram", "atr_pct", "adx_14", "bb_width", "relative_volume",
    "return_1d", "return_5d", "return_20d", "realized_volatility_20d",
    "spy_return_5d", "spy_return_20d", "qqq_return_5d", "qqq_return_20d",
    "sector_return_5d", "sector_return_20d", "vix", "vix_change",
]


@dataclass(frozen=True)
class TimeSplit:
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray


@dataclass
class TrainedModel:
    classifier: object
    regressor: object
    classifier_name: str
    regressor_name: str
    calibration_method: str
    feature_names: list[str]
    evaluation_metrics: dict[str, float | int | str | None] | None = None
    residual_downside_quantile: float = 0.0
    model_version: str = MODEL_VERSION

    def serialize(self) -> str:
        buffer = BytesIO()
        joblib.dump(self, buffer)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @classmethod
    def deserialize(cls, artifact: str) -> "TrainedModel":
        value = joblib.load(BytesIO(base64.b64decode(artifact)))
        if not isinstance(value, cls):
            raise ValueError("Unexpected model artifact type")
        return value


@dataclass(frozen=True)
class EvaluationResult:
    metrics: dict[str, float | int | str | None]
    out_of_sample: pd.DataFrame
    model: TrainedModel | None
    status: str


def prepare_training_dataset(
    features: pd.DataFrame,
    prices: pd.DataFrame,
    horizon_days: int = PRIMARY_HORIZON,
) -> pd.DataFrame:
    """Creates future targets outside the persisted feature table."""
    if horizon_days < 1:
        raise ValueError("horizon_days must be positive")
    feature_data = features.copy()
    price_data = prices[["ticker", "timestamp", "close"]].copy()
    for frame in (feature_data, price_data):
        frame["ticker"] = frame["ticker"].astype(str).str.upper()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    price_data = price_data.sort_values(["ticker", "timestamp"])
    price_data["future_close"] = price_data.groupby("ticker")["close"].shift(-horizon_days)
    price_data["future_return"] = price_data["future_close"] / price_data["close"] - 1
    price_data["direction_up"] = (price_data["future_return"] > 0).astype(int)
    merged = feature_data.merge(
        price_data[["ticker", "timestamp", "close", "future_return", "direction_up"]],
        on=["ticker", "timestamp"],
        how="inner",
        validate="one_to_one",
    )
    return merged.dropna(subset=["future_return"]).sort_values(["timestamp", "ticker"]).reset_index(drop=True)


def expanding_purged_splits(
    timestamps: pd.Series,
    horizon_days: int = PRIMARY_HORIZON,
    min_train_days: int = MIN_TRAIN_DAYS,
    validation_days: int = CALIBRATION_DAYS,
    test_days: int = TEST_DAYS,
) -> list[TimeSplit]:
    dates = np.array(sorted(pd.to_datetime(timestamps, utc=True).dt.normalize().unique()))
    splits: list[TimeSplit] = []
    cursor = min_train_days
    while cursor + horizon_days + validation_days + horizon_days + test_days <= len(dates):
        train_dates = dates[:cursor]
        validation_start = cursor + horizon_days
        validation_dates = dates[validation_start:validation_start + validation_days]
        test_start = validation_start + validation_days + horizon_days
        test_dates = dates[test_start:test_start + test_days]
        normalized = pd.to_datetime(timestamps, utc=True).dt.normalize().to_numpy()
        splits.append(TimeSplit(
            train=np.flatnonzero(np.isin(normalized, train_dates)),
            validation=np.flatnonzero(np.isin(normalized, validation_dates)),
            test=np.flatnonzero(np.isin(normalized, test_dates)),
        ))
        cursor += test_days
    return splits


class WalkForwardTrainer:
    def __init__(self, horizon_days: int = PRIMARY_HORIZON):
        self.horizon_days = horizon_days

    @staticmethod
    def _classifiers() -> dict[str, object]:
        return {
            "logistic_regression": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
            ]),
            "hist_gradient_boosting": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("model", HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, random_state=42)),
            ]),
            "random_forest": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestClassifier(
                    n_estimators=200, min_samples_leaf=10, class_weight="balanced_subsample",
                    n_jobs=-1, random_state=42,
                )),
            ]),
        }

    @staticmethod
    def _regressors() -> dict[str, object]:
        return {
            "ridge": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=10.0)),
            ]),
            "hist_gradient_boosting": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("model", HistGradientBoostingRegressor(
                    loss="absolute_error", max_iter=150, learning_rate=0.05, random_state=42,
                )),
            ]),
        }

    def evaluate(self, dataset: pd.DataFrame) -> EvaluationResult:
        missing = set(MODEL_FEATURES + ["timestamp", "direction_up", "future_return"]) - set(dataset.columns)
        if missing:
            raise ValueError(f"Training dataset is missing columns: {sorted(missing)}")
        splits = expanding_purged_splits(dataset["timestamp"], self.horizon_days)
        if not splits:
            return EvaluationResult({}, pd.DataFrame(), None, "insufficient_historical_validation_data")

        predictions = []
        last_model: TrainedModel | None = None
        for fold_number, split in enumerate(splits, start=1):
            train = dataset.iloc[split.train]
            validation = dataset.iloc[split.validation]
            test = dataset.iloc[split.test]
            if (
                len(validation) < MIN_CALIBRATION_SAMPLES
                or train["direction_up"].nunique() < 2
                or validation["direction_up"].nunique() < 2
            ):
                continue
            model = self._fit_selected(train, validation)
            probabilities = model.classifier.predict_proba(test[MODEL_FEATURES])[:, 1]
            expected_returns = model.regressor.predict(test[MODEL_FEATURES])
            fold = test[["ticker", "timestamp", "future_return", "direction_up"]].copy()
            fold["probability_up"] = probabilities
            fold["expected_return"] = expected_returns
            fold["fold"] = fold_number
            predictions.append(fold)
            last_model = model
        if not predictions or last_model is None:
            return EvaluationResult({}, pd.DataFrame(), None, "insufficient_historical_validation_data")

        out_of_sample = pd.concat(predictions, ignore_index=True)
        metrics = self._metrics(out_of_sample)
        metrics.update({
            "classifier_name": last_model.classifier_name,
            "regressor_name": last_model.regressor_name,
            "calibration_method": last_model.calibration_method,
        })
        residuals = out_of_sample["future_return"] - out_of_sample["expected_return"]
        last_model.evaluation_metrics = metrics.copy()
        last_model.residual_downside_quantile = float(residuals.quantile(0.1))
        return EvaluationResult(metrics, out_of_sample, last_model, "validated")

    def fit_latest(self, dataset: pd.DataFrame) -> TrainedModel | None:
        dates = np.array(sorted(pd.to_datetime(dataset["timestamp"], utc=True).dt.normalize().unique()))
        required = MIN_TRAIN_DAYS + self.horizon_days + CALIBRATION_DAYS
        if len(dates) < required:
            return None
        calibration_dates = dates[-CALIBRATION_DAYS:]
        cutoff = dates[-CALIBRATION_DAYS - self.horizon_days]
        train = dataset[pd.to_datetime(dataset["timestamp"], utc=True).dt.normalize() < cutoff]
        validation = dataset[pd.to_datetime(dataset["timestamp"], utc=True).dt.normalize().isin(calibration_dates)]
        if (
            len(validation) < MIN_CALIBRATION_SAMPLES
            or train["direction_up"].nunique() < 2
            or validation["direction_up"].nunique() < 2
        ):
            return None
        return self._fit_selected(train, validation)

    def _fit_selected(self, train: pd.DataFrame, validation: pd.DataFrame) -> TrainedModel:
        train_x = train[MODEL_FEATURES]
        validation_x = validation[MODEL_FEATURES]
        best_classifier_name = ""
        best_classifier = None
        best_brier = math.inf
        for name, candidate in self._classifiers().items():
            fitted = clone(candidate).fit(train_x, train["direction_up"])
            score = brier_score_loss(validation["direction_up"], fitted.predict_proba(validation_x)[:, 1])
            if score < best_brier:
                best_classifier_name, best_classifier, best_brier = name, fitted, score

        best_regressor_name = ""
        best_regressor = None
        best_mae = math.inf
        for name, candidate in self._regressors().items():
            fitted = clone(candidate).fit(train_x, train["future_return"])
            score = mean_absolute_error(validation["future_return"], fitted.predict(validation_x))
            if score < best_mae:
                best_regressor_name, best_regressor, best_mae = name, fitted, score

        calibration_method = "isotonic" if len(validation) >= 1000 else "sigmoid"
        calibrated = CalibratedClassifierCV(
            FrozenEstimator(best_classifier), method=calibration_method,
        ).fit(validation_x, validation["direction_up"])
        return TrainedModel(
            classifier=calibrated,
            regressor=best_regressor,
            classifier_name=best_classifier_name,
            regressor_name=best_regressor_name,
            calibration_method=calibration_method,
            feature_names=MODEL_FEATURES.copy(),
        )

    @staticmethod
    def _metrics(rows: pd.DataFrame) -> dict[str, float | int | None]:
        actual = rows["direction_up"]
        probability = rows["probability_up"].clip(1e-6, 1 - 1e-6)
        predicted_return = rows["expected_return"]
        metrics: dict[str, float | int | None] = {
            "sample_count": len(rows),
            "auc": float(roc_auc_score(actual, probability)) if actual.nunique() > 1 else None,
            "brier_score": float(brier_score_loss(actual, probability)),
            "log_loss": float(log_loss(actual, probability)),
            "directional_accuracy": float(accuracy_score(actual, probability >= 0.5)),
            "mae": float(mean_absolute_error(rows["future_return"], predicted_return)),
            "rmse": float(mean_squared_error(rows["future_return"], predicted_return) ** 0.5),
        }
        ranked = rows.sort_values(["timestamp", "expected_return"], ascending=[True, False])
        for size in (5, 10, 20):
            top = ranked.groupby("timestamp", group_keys=False).head(size)
            metrics[f"top_{size}_mean_return"] = float(top["future_return"].mean()) if not top.empty else None
        spy_rows = rows[rows["ticker"] == "SPY"]
        metrics["spy_mean_return"] = float(spy_rows["future_return"].mean()) if not spy_rows.empty else None
        baseline_brier = float(((actual - actual.mean()) ** 2).mean())
        metrics["reliability"] = max(0.0, 1 - metrics["brier_score"] / baseline_brier) if baseline_brier else 0.0
        return metrics