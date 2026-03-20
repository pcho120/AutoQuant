import pytest
from unittest.mock import Mock
from datetime import datetime
from services.trading_service import TradingService
from domain.position import Order, Position


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
    """Test successful BUY order execution."""
    order = Order(
        ticker="AAPL",
        action="BUY",
        quantity=10,
        price=150.0,
        timestamp=datetime.now()
    )
    cash_balance = 2000.0
    
    result = trading_service.execute_order(user_id="user123", order=order, cash_balance=cash_balance)
    
    assert result["status"] == "SUCCESS"
    assert "remaining_cash" in result
    assert "fee" in result
    
    # Total cost = (10 * 150) + fee
    # Fee = 10 * 150 * 0.001 = 1.5
    # Total cost = 1500 + 1.5 = 1501.5
    # Remaining cash = 2000 - 1501.5 = 498.5
    
    assert abs(result["remaining_cash"] - 498.5) < 0.01
    assert abs(result["fee"] - 1.5) < 0.01
    mock_db.save_order.assert_called_once_with("user123", order)


def test_execute_order_buy_insufficient_cash(trading_service, mock_db):
    """Test BUY order failure due to insufficient cash."""
    order = Order(
        ticker="AAPL",
        action="BUY",
        quantity=10,
        price=150.0,
        timestamp=datetime.now()
    )
    cash_balance = 100.0  # Not enough cash
    
    result = trading_service.execute_order(user_id="user123", order=order, cash_balance=cash_balance)
    
    assert result["status"] == "FAILED"
    assert result["reason"] == "Insufficient cash"
    mock_db.save_order.assert_not_called()


def test_execute_order_sell_success(trading_service, mock_db):
    """Test successful SELL order execution."""
    # Mock existing position
    existing_position = Position(ticker="AAPL", quantity=20, buy_price=140.0, current_price=150.0)
    mock_db.fetch_positions.return_value = [existing_position]
    
    order = Order(
        ticker="AAPL",
        action="SELL",
        quantity=10,
        price=160.0,
        timestamp=datetime.now()
    )
    cash_balance = 1000.0
    
    result = trading_service.execute_order(user_id="user123", order=order, cash_balance=cash_balance)
    
    assert result["status"] == "SUCCESS"
    assert "remaining_cash" in result
    assert "fee" in result
    
    # Sale proceeds = (10 * 160) - fee
    # Fee = 10 * 160 * 0.001 = 1.6
    # Sale proceeds = 1600 - 1.6 = 1598.4
    # Remaining cash = 1000 + 1598.4 = 2598.4
    
    assert abs(result["remaining_cash"] - 2598.4) < 0.01
    assert abs(result["fee"] - 1.6) < 0.01
    mock_db.save_order.assert_called_once_with("user123", order)


def test_execute_order_sell_insufficient_quantity(trading_service, mock_db):
    """Test SELL order failure due to insufficient quantity."""
    # Mock existing position with less quantity
    existing_position = Position(ticker="AAPL", quantity=5, buy_price=140.0, current_price=150.0)
    mock_db.fetch_positions.return_value = [existing_position]
    
    order = Order(
        ticker="AAPL",
        action="SELL",
        quantity=10,  # Trying to sell more than owned
        price=160.0,
        timestamp=datetime.now()
    )
    cash_balance = 1000.0
    
    result = trading_service.execute_order(user_id="user123", order=order, cash_balance=cash_balance)
    
    assert result["status"] == "FAILED"
    assert result["reason"] == "Insufficient quantity"
    mock_db.save_order.assert_not_called()


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
