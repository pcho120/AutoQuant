import pandas as pd

from services.prediction_service import PredictionService


def test_classify_macd_golden_cross():
    histogram = pd.Series([-0.20, -0.10, -0.03, 0.02])

    assert PredictionService._classify_macd_cross(histogram) == "Golden Cross"


def test_classify_approaching_macd_golden_cross():
    histogram = pd.Series([-0.20, -0.12, -0.06, -0.03, -0.01])

    assert PredictionService._classify_macd_cross(histogram) == "Approaching"


def test_classify_macd_ignores_distant_or_falling_signal():
    distant = pd.Series([-0.10, -0.20, -0.30, -0.40, -0.50])

    assert PredictionService._classify_macd_cross(distant) is None