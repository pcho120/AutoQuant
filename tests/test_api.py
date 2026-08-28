from datetime import datetime, timezone
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

import api
from api import build_market_payload
from adapters.webull_portfolio import WebullPortfolio
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


def test_sync_webull_portfolio_updates_supabase(monkeypatch):
    database = Mock()
    database.save_positions.return_value = True
    webull = Mock()
    webull.fetch_portfolio.return_value = WebullPortfolio(
        account_count=1,
        positions=[Position("TSLA", 4, 210, 0)],
    )
    monkeypatch.setattr(api, "get_db_client", lambda: database)
    monkeypatch.setattr(api, "get_webull_portfolio", lambda: webull)

    response = TestClient(api.app).post("/api/portfolio/default_user/sync-webull")

    assert response.status_code == 200
    assert response.json() == {"userId": "default_user", "accounts": 1, "synced": 1}
    database.save_positions.assert_called_once_with(
        "default_user",
        [Position("TSLA", 4, 210, 0)],
        table_name="portfolio",
    )


def test_sync_webull_portfolio_does_not_touch_db_when_webull_fails(monkeypatch):
    database = Mock()
    webull = Mock()
    webull.fetch_portfolio.side_effect = ValueError("No Webull accounts were returned")
    monkeypatch.setattr(api, "get_db_client", lambda: database)
    monkeypatch.setattr(api, "get_webull_portfolio", lambda: webull)

    response = TestClient(api.app).post("/api/portfolio/default_user/sync-webull")

    assert response.status_code == 400
    database.save_positions.assert_not_called()


def test_sync_webull_portfolio_reports_supabase_failure(monkeypatch):
    database = Mock()
    database.save_positions.return_value = False
    webull = Mock()
    webull.fetch_portfolio.return_value = WebullPortfolio(
        account_count=1,
        positions=[Position("AAPL", 1, 100, 0)],
    )
    monkeypatch.setattr(api, "get_db_client", lambda: database)
    monkeypatch.setattr(api, "get_webull_portfolio", lambda: webull)

    response = TestClient(api.app).post("/api/portfolio/default_user/sync-webull")

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to save Webull portfolio to Supabase"


def test_paper_portfolio_uses_isolated_table_and_live_prices(monkeypatch):
    database = Mock()
    database.fetch_positions.return_value = [Position("AAPL", 3, 150, 0)]
    market = Mock()
    market.fetch_current_prices.return_value = {"AAPL": 210.0}
    monkeypatch.setattr(api, "get_db_client", lambda: database)
    monkeypatch.setattr(api, "get_market_data", lambda: market)

    response = TestClient(api.app).get("/api/paper-trading/user123")

    assert response.status_code == 200
    assert response.json()["positions"][0]["currentPrice"] == 210.0
    database.fetch_positions.assert_called_once_with("user123", table_name="paper_portfolio")


def test_save_paper_portfolio_replaces_isolated_holdings(monkeypatch):
    database = Mock()
    monkeypatch.setattr(api, "get_db_client", lambda: database)

    response = TestClient(api.app).put(
        "/api/paper-trading/user123",
        json={"positions": [{"ticker": " tsla ", "quantity": 2, "buyPrice": 0}]},
    )

    assert response.status_code == 200
    database.save_positions.assert_called_once_with(
        "user123", [Position("TSLA", 2, 0, 0.0)], table_name="paper_portfolio",
    )


def test_execute_paper_order_uses_existing_trading_service(monkeypatch):
    service = Mock()
    service.execute_order.return_value = {"status": "SUCCESS", "remaining_cash": 8498.5, "fee": 1.5}
    monkeypatch.setattr(api, "get_trading_service", lambda: service)

    response = TestClient(api.app).post(
        "/api/paper-trading/user123/orders",
        json={"ticker": " aapl ", "action": "BUY", "quantity": 10, "price": 150, "cashBalance": 10000},
    )

    assert response.status_code == 200
    order = service.execute_order.call_args.args[1]
    assert (order.ticker, order.action, order.quantity, order.price) == ("AAPL", "BUY", 10, 150)


def cached_prediction(ticker="AAPL", expected_return=0.05, probability_up=0.72):
    return {
        "ticker": ticker, "horizon": "5d", "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
        "current_price": 200, "expected_return": expected_return, "predicted_price": 210,
        "probability_up": probability_up, "downside_risk": 0.03, "risk_reward": 1.67,
        "signal": "BUY", "reliability": 0.18, "reliability_status": "validated",
        "model_version": "prediction-v1.0.0", "feature_version": "features-v1.0.0",
        "explanation": {"bullish_factors": ["Positive momentum"], "risk_factors": []},
    }


def test_predict_price_returns_cached_calibrated_result(monkeypatch):
    repository = Mock()
    repository.fetch_latest_prediction.return_value = cached_prediction()
    repository.fetch_recent_news.return_value = []
    monkeypatch.setattr(api, "get_collection_repository", lambda: repository)

    response = TestClient(api.app).post(
        "/api/predictions",
        json={"ticker": "aapl", "horizon": "5d", "includeNews": True, "includeIndicators": True},
    )

    assert response.status_code == 200
    assert response.json()["expectedReturn"] == 0.05
    assert response.json()["probabilityUp"] == 0.72
    assert "confidence" not in response.json()
    repository.fetch_latest_prediction.assert_called_once_with("AAPL", "5d")


def test_prediction_missing_returns_honest_status(monkeypatch):
    repository = Mock()
    repository.fetch_latest_prediction.return_value = None
    monkeypatch.setattr(api, "get_collection_repository", lambda: repository)

    response = TestClient(api.app).get("/api/predictions/NVDA")

    assert response.status_code == 404
    assert response.json()["detail"] == "Insufficient historical validation data"


def test_prediction_screener_sorts_latest_rows(monkeypatch):
    repository = Mock()
    repository.fetch_latest_predictions.return_value = [
        cached_prediction("AAPL", 0.03, 0.80),
        cached_prediction("NVDA", 0.08, 0.65),
    ]
    monkeypatch.setattr(api, "get_collection_repository", lambda: repository)

    response = TestClient(api.app).get("/api/predictions/screener?sort=expected_return")

    assert response.status_code == 200
    assert [row["ticker"] for row in response.json()["results"]] == ["NVDA", "AAPL"]


def test_macd_scan_maps_existing_result_shape(monkeypatch):
    service = Mock()
    service.scan_macd_golden_crosses.return_value = [{
        "Ticker": "MSFT", "Name": "Microsoft", "Status": "Golden Cross",
        "Current Price": 500, "Predicted Price (5d)": 510, "Expected Change (%)": 2,
    }]
    monkeypatch.setattr(api, "get_prediction_service", lambda: service)

    response = TestClient(api.app).post("/api/predictions/scan-macd")

    assert response.status_code == 200
    assert response.json()["results"][0] == {
        "ticker": "MSFT", "name": "Microsoft", "status": "Golden Cross",
        "currentPrice": 500, "predictedPrice": 510, "expectedChangePercent": 2,
    }