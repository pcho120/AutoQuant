from unittest.mock import Mock

import pytest

from domain.prediction import PredictionRequest
from services.prediction_service import PredictionService


def test_rule_based_prediction_is_retired_instead_of_faking_confidence():
    service = PredictionService(Mock(), Mock())

    with pytest.raises(RuntimeError, match="validated cached prediction"):
        service.predict_price(PredictionRequest("AAPL", "5d", True, True))