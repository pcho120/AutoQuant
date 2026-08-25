import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

import api
from api import build_market_payload
from domain.position import Position


def test_build_market_payload_includes_all_chart_series():
    index = pd.date_range("2026-01-01", periods=40, freq="D", tz="UTC")
    history = pd.DataFrame(
        {
            "Open": [100 + index for index in range(40)],
            "High": [102 + index for index in range(40)],
            "Low": [99 + index for index in range(40)],
            "Close": [101 + index for index in range(40)],
            "Volume": [1_000_000 + index for index in range(40)],
        },
        index=index,
    )

    payload = build_market_payload("aapl", "1mo", "1d", history)

    assert payload["ticker"] == "AAPL"
    assert len(payload["candles"]) == 40
    assert len(payload["volume"]) == 40
    assert payload["rsi"]
    assert len(payload["macd"]) == 40
    assert payload["candles"][0]["time"] == int(index[0].timestamp())


def test_build_market_payload_rejects_empty_history():
    with pytest.raises(ValueError, match="No market data"):
        build_market_payload("AAPL", "1mo", "1d", pd.DataFrame())


def test_portfolio_uses_live_prices(monkeypatch):
    database = Mock()
    database.fetch_positions.return_value = [Position("AAPL", 10, 150, 0)]
    market = Mock()
    market.fetch_current_prices.return_value = {"AAPL": 200.0}
    monkeypatch.setattr(api, "get_db_client", lambda: database)
    monkeypatch.setattr(api, "get_market_data", lambda: market)

    response = TestClient(api.app).get("/api/portfolio/default_user")

    assert response.status_code == 200
    assert response.json()["positions"][0]["currentPrice"] == 200.0


def test_save_portfolio_normalizes_and_persists_positions(monkeypatch):
    database = Mock()
    monkeypatch.setattr(api, "get_db_client", lambda: database)

    response = TestClient(api.app).put(
        "/api/portfolio/default_user",
        json={"positions": [{"ticker": " aapl ", "quantity": 12, "buyPrice": 155.5}]},
    )

    assert response.status_code == 200
    assert response.json() == {"userId": "default_user", "saved": 1}
    saved_positions = database.save_positions.call_args.args[1]
    assert saved_positions == [Position("AAPL", 12, 155.5, 0.0)]