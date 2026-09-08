import pytest
from unittest.mock import Mock
from services.trading_service import TradingService
from domain.position import Position


@pytest.fixture
def mock_db():
    """Mock database adapter."""
    return Mock()


@pytest.fixture
def mock_market():
    """Mock market data adapter."""
    return Mock()


@pytest.fixture
def trading_service(mock_db, mock_market):
    """Create trading service with mocked dependencies."""
    return TradingService(db=mock_db, market=mock_market)


def test_execute_order_buy_success(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": True,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }
    mock_db.execute_paper_order.return_value = {
        "status": "SUCCESS", "remaining_cash": 8498.25, "fee": 1.50075,
        "filled_price": 150.075, "quantity": 10,
    }

    result = trading_service.execute_order("user123", "AAPL", "BUY", 10, "MARKET")

    assert result["status"] == "SUCCESS"
    assert result["filled_price"] == pytest.approx(150.075)
    assert result["quote_price"] == 150.0
    assert mock_db.execute_paper_order.call_args.kwargs["filled_price"] == pytest.approx(150.075)


def test_execute_order_buy_insufficient_cash(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": True,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }
    mock_db.execute_paper_order.side_effect = Exception("Insufficient cash")

    result = trading_service.execute_order("user123", "AAPL", "BUY", 10, "MARKET")

    assert result["status"] == "FAILED"
    assert result["reason"] == "Insufficient cash"


def test_execute_order_sell_success(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 160.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": True,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }
    mock_db.execute_paper_order.return_value = {
        "status": "SUCCESS", "remaining_cash": 11598.4, "fee": 1.5992,
        "filled_price": 159.92, "quantity": 10,
    }

    result = trading_service.execute_order("user123", "AAPL", "SELL", 10, "MARKET")

    assert result["status"] == "SUCCESS"
    assert mock_db.execute_paper_order.call_args.kwargs["filled_price"] == pytest.approx(159.92)


def test_execute_order_sell_insufficient_quantity(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 160.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": True,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }
    mock_db.execute_paper_order.side_effect = Exception("Insufficient quantity")

    result = trading_service.execute_order("user123", "AAPL", "SELL", 10, "MARKET")

    assert result["status"] == "FAILED"
    assert result["reason"] == "Insufficient quantity"


def test_limit_order_requires_reachable_price(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": True,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }

    result = trading_service.execute_order("user123", "AAPL", "BUY", 1, "LIMIT", 149.0)

    assert result == {"status": "FAILED", "reason": "Limit price has not been reached"}
    mock_db.execute_paper_order.assert_not_called()


def test_stale_quote_rejects_order(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T15:30:00+00:00", "marketOpen": False,
        "regularSession": True, "afterHoursBuyAllowed": False,
    }

    result = trading_service.execute_order("user123", "AAPL", "BUY", 1, "MARKET")

    assert result == {"status": "FAILED", "reason": "The live market quote is stale"}
    mock_db.execute_paper_order.assert_not_called()


def test_large_order_is_capped_by_simulated_liquidity(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T15:30:00+00:00",
        "marketOpen": True, "regularSession": True, "afterHoursBuyAllowed": False,
        "availableQuantity": 25.0,
    }
    mock_db.execute_paper_order.return_value = {
        "status": "SUCCESS", "remaining_cash": 96000, "fee": 3.75,
        "filled_price": 150.075, "requested_quantity": 100,
        "quantity": 25, "partial_fill": True,
    }

    result = trading_service.execute_order("user123", "AAPL", "BUY", 100, "MARKET")

    assert result["partial_fill"] is True
    assert mock_db.execute_paper_order.call_args.kwargs["requested_quantity"] == 100
    assert mock_db.execute_paper_order.call_args.kwargs["filled_quantity"] == 25


def test_closed_session_buy_fills_at_last_close_without_slippage(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T20:00:00+00:00", "marketOpen": False,
        "regularSession": False, "afterHoursBuyAllowed": True, "availableQuantity": 25.0,
    }
    mock_db.execute_paper_order.return_value = {
        "status": "SUCCESS", "remaining_cash": 98498.5, "fee": 1.5,
        "filled_price": 150.0, "requested_quantity": 10,
        "quantity": 10, "partial_fill": False,
    }

    result = trading_service.execute_order("user123", "AAPL", "BUY", 10, "MARKET")

    assert result["execution_session"] == "CLOSED"
    assert mock_db.execute_paper_order.call_args.kwargs["filled_price"] == 150.0
    assert mock_db.execute_paper_order.call_args.kwargs["execution_session"] == "CLOSED"


def test_closed_session_sell_is_rejected(trading_service, mock_db):
    trading_service.market.fetch_trade_quote.return_value = {
        "price": 150.0, "timestamp": "2026-09-04T20:00:00+00:00", "marketOpen": False,
        "regularSession": False, "afterHoursBuyAllowed": True,
    }

    result = trading_service.execute_order("user123", "AAPL", "SELL", 10, "MARKET")

    assert result == {"status": "FAILED", "reason": "Sell orders require an open regular market"}
    mock_db.execute_paper_order.assert_not_called()


def test_calculate_pnl_basic(trading_service):
    """Test P/L calculation with multiple positions."""
    positions = [
        Position(ticker="AAPL", quantity=10, buy_price=150.0, current_price=160.0),
        Position(ticker="MSFT", quantity=5, buy_price=300.0, current_price=320.0),
    ]
    
    result = trading_service.calculate_pnl(positions)
    
    # AAPL P/L: 10 * (160 - 150) = 100
    # MSFT P/L: 5 * (320 - 300) = 100
    # Total P/L = 200
    # Total invested = (10 * 150) + (5 * 300) = 1500 + 1500 = 3000
    # P/L percent = (200 / 3000) * 100 = 6.67%
    
    assert abs(result["total_pnl_dollars"] - 200.0) < 0.01
    assert abs(result["total_pnl_percent"] - 6.67) < 0.1
    assert result["position_count"] == 2


def test_calculate_pnl_empty(trading_service):
    """Test P/L calculation with empty positions."""
    result = trading_service.calculate_pnl(positions=[])
    
    assert result["total_pnl_dollars"] == 0.0
    assert result["total_pnl_percent"] == 0.0
    assert result["position_count"] == 0
