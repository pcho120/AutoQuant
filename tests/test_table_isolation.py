"""
Integration tests verifying table isolation between portfolio and paper_portfolio routes.

This test suite ensures that:
1. PortfolioService operations route to 'portfolio' table exclusively
2. TradingService SELL operations route to 'paper_portfolio' table exclusively
3. No cross-contamination occurs between the two table routes
"""

import pytest
from unittest.mock import Mock, MagicMock, call
import pandas as pd
from services.portfolio_service import PortfolioService
from services.trading_service import TradingService
from domain.position import Position, Order, Portfolio
from datetime import datetime


@pytest.fixture
def mock_db():
    """Mock database adapter with spies for table routing verification."""
    db = Mock()
    db.fetch_positions = Mock(return_value=[])
    db.save_positions = Mock(return_value=None)
    db.update_position = Mock(return_value=True)
    db.delete_position = Mock(return_value=True)
    db.save_order = Mock(return_value=True)
    return db


@pytest.fixture
def mock_market():
    """Mock market data adapter."""
    market = Mock()
    market.fetch_current_prices = Mock(return_value={})
    return market


# ============================================================================
# SCENARIO 1: Portfolio Service Routes to 'portfolio' Table Only
# ============================================================================

def test_portfolio_service_get_portfolio_uses_portfolio_table(mock_db, mock_market):
    """Verify PortfolioService.get_portfolio() routes to 'portfolio' table."""
    # Arrange
    mock_db.fetch_positions.return_value = [
        Position(ticker="AAPL", quantity=10.0, buy_price=150.0, current_price=160.0)
    ]
    service = PortfolioService(db=mock_db, market=mock_market)
    
    # Act
    service.get_portfolio.clear()  # Clear streamlit cache
    portfolio = service.get_portfolio(user_id="test_user")
    
    # Assert
    mock_db.fetch_positions.assert_called_once_with("test_user", table_name="portfolio")
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].ticker == "AAPL"


def test_portfolio_service_update_positions_uses_portfolio_table(mock_db, mock_market):
    """Verify PortfolioService.update_positions() routes to 'portfolio' table."""
    # Arrange
    service = PortfolioService(db=mock_db, market=mock_market)
    df = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT"],
        "Quantity": [10.0, 5.0],
        "Buy Price": [150.0, 300.0],
        "Current Price": [160.0, 320.0]
    })
    
    # Act
    result = service.update_positions(user_id="test_user", edited_df=df)
    
    # Assert
    assert result is True
    mock_db.save_positions.assert_called_once()
    
    # Verify the call includes table_name="portfolio"
    call_args = mock_db.save_positions.call_args
    assert call_args[0][0] == "test_user"  # user_id
    assert call_args[1]["table_name"] == "portfolio"  # keyword arg
    
    # Verify positions passed
    positions = call_args[0][1]
    assert len(positions) == 2
    assert positions[0].ticker == "AAPL"
    assert positions[1].ticker == "MSFT"


def test_portfolio_service_never_calls_paper_portfolio_table(mock_db, mock_market):
    """Verify PortfolioService never accesses 'paper_portfolio' table."""
    # Arrange
    mock_db.fetch_positions.return_value = [
        Position(ticker="AAPL", quantity=10.0, buy_price=150.0, current_price=160.0)
    ]
    service = PortfolioService(db=mock_db, market=mock_market)
    df = pd.DataFrame({
        "Ticker": ["AAPL"],
        "Quantity": [10.0],
        "Buy Price": [150.0],
        "Current Price": [160.0]
    })
    
    # Act
    service.get_portfolio.clear()
    service.get_portfolio(user_id="test_user")
    service.update_positions(user_id="test_user", edited_df=df)
    
    # Assert - check all calls to verify none use "paper_portfolio"
    for call_obj in mock_db.fetch_positions.call_args_list:
        if len(call_obj[1]) > 0 and "table_name" in call_obj[1]:
            assert call_obj[1]["table_name"] != "paper_portfolio", \
                "PortfolioService must never access paper_portfolio table"
    
    for call_obj in mock_db.save_positions.call_args_list:
        if len(call_obj[1]) > 0 and "table_name" in call_obj[1]:
            assert call_obj[1]["table_name"] != "paper_portfolio", \
                "PortfolioService must never write to paper_portfolio table"


# ============================================================================
# SCENARIO 2: TradingService SELL Routes to 'paper_portfolio' Table Only
# ============================================================================

def test_trading_service_sell_order_uses_paper_portfolio_table(mock_db, mock_market):
    """Verify TradingService.execute_order(SELL) routes to 'paper_portfolio' table."""
    # Arrange
    existing_position = Position(ticker="AAPL", quantity=20.0, buy_price=140.0, current_price=150.0)
    mock_db.fetch_positions.return_value = [existing_position]
    
    service = TradingService(db=mock_db, market=mock_market)
    order = Order(
        ticker="AAPL",
        action="SELL",
        quantity=10.0,
        price=160.0,
        timestamp=datetime.now()
    )
    
    # Act
    result = service.execute_order(user_id="test_user", order=order, cash_balance=1000.0)
    
    # Assert
    assert result["status"] == "SUCCESS"
    mock_db.fetch_positions.assert_called_once_with("test_user", table_name="paper_portfolio")
    mock_db.save_order.assert_called_once()


def test_trading_service_buy_order_does_not_fetch_positions(mock_db, mock_market):
    """Verify TradingService.execute_order(BUY) does not fetch positions (no table access)."""
    # Arrange
    service = TradingService(db=mock_db, market=mock_market)
    order = Order(
        ticker="AAPL",
        action="BUY",
        quantity=10.0,
        price=150.0,
        timestamp=datetime.now()
    )
    
    # Act
    result = service.execute_order(user_id="test_user", order=order, cash_balance=2000.0)
    
    # Assert
    assert result["status"] == "SUCCESS"
    mock_db.fetch_positions.assert_not_called()  # BUY does not need position validation
    mock_db.save_order.assert_called_once()


def test_trading_service_never_calls_portfolio_table(mock_db, mock_market):
    """Verify TradingService never accesses 'portfolio' table."""
    # Arrange
    existing_position = Position(ticker="AAPL", quantity=20.0, buy_price=140.0, current_price=150.0)
    mock_db.fetch_positions.return_value = [existing_position]
    
    service = TradingService(db=mock_db, market=mock_market)
    order = Order(
        ticker="AAPL",
        action="SELL",
        quantity=10.0,
        price=160.0,
        timestamp=datetime.now()
    )
    
    # Act
    service.execute_order(user_id="test_user", order=order, cash_balance=1000.0)
    
    # Assert - check all calls to verify none use "portfolio"
    for call_obj in mock_db.fetch_positions.call_args_list:
        if len(call_obj[1]) > 0 and "table_name" in call_obj[1]:
            assert call_obj[1]["table_name"] != "portfolio", \
                "TradingService must never access portfolio table"


# ============================================================================
# SCENARIO 3: No Cross-Contamination Between Routes
# ============================================================================

def test_no_cross_contamination_portfolio_and_paper_trading_isolation(mock_db, mock_market):
    """
    Integration test verifying portfolio and paper trading operate on separate tables.
    
    This test simulates concurrent usage of both portfolio and paper trading features
    to ensure they maintain complete isolation at the table level.
    """
    # Arrange - Set up mock responses for both tables
    portfolio_positions = [
        Position(ticker="AAPL", quantity=100.0, buy_price=120.0, current_price=150.0)
    ]
    paper_positions = [
        Position(ticker="MSFT", quantity=50.0, buy_price=250.0, current_price=300.0)
    ]
    
    # Mock DB to return different positions based on table_name
    def fetch_positions_side_effect(user_id, table_name="portfolio"):
        if table_name == "portfolio":
            return portfolio_positions
        elif table_name == "paper_portfolio":
            return paper_positions
        return []
    
    mock_db.fetch_positions.side_effect = fetch_positions_side_effect
    
    # Create both services
    portfolio_service = PortfolioService(db=mock_db, market=mock_market)
    trading_service = TradingService(db=mock_db, market=mock_market)
    
    # Act - Perform operations on both services
    portfolio_service.get_portfolio.clear()
    portfolio = portfolio_service.get_portfolio(user_id="test_user")
    
    sell_order = Order(
        ticker="MSFT",
        action="SELL",
        quantity=10.0,
        price=310.0,
        timestamp=datetime.now()
    )
    trade_result = trading_service.execute_order(
        user_id="test_user",
        order=sell_order,
        cash_balance=5000.0
    )
    
    # Assert - Verify correct table routing
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].ticker == "AAPL"  # Portfolio data
    
    assert trade_result["status"] == "SUCCESS"  # Paper trading succeeded
    
    # Verify calls routed to correct tables
    fetch_calls = mock_db.fetch_positions.call_args_list
    assert len(fetch_calls) == 2
    
    # First call: PortfolioService → portfolio table
    assert fetch_calls[0][0][0] == "test_user"
    assert fetch_calls[0][1]["table_name"] == "portfolio"
    
    # Second call: TradingService → paper_portfolio table
    assert fetch_calls[1][0][0] == "test_user"
    assert fetch_calls[1][1]["table_name"] == "paper_portfolio"


def test_isolation_portfolio_update_does_not_affect_paper_trading(mock_db, mock_market):
    """
    Verify that updating portfolio positions does not affect paper trading positions.
    """
    # Arrange
    portfolio_service = PortfolioService(db=mock_db, market=mock_market)
    df = pd.DataFrame({
        "Ticker": ["AAPL"],
        "Quantity": [200.0],
        "Buy Price": [130.0],
        "Current Price": [160.0]
    })
    
    # Act
    result = portfolio_service.update_positions(user_id="test_user", edited_df=df)
    
    # Assert
    assert result is True
    
    # Verify save_positions was called with portfolio table
    save_call = mock_db.save_positions.call_args
    assert save_call[0][0] == "test_user"
    assert save_call[1]["table_name"] == "portfolio"
    
    # Verify no calls were made to paper_portfolio
    for call_obj in mock_db.save_positions.call_args_list:
        if len(call_obj[1]) > 0 and "table_name" in call_obj[1]:
            assert call_obj[1]["table_name"] != "paper_portfolio", \
                "Portfolio update must not affect paper_portfolio table"


def test_isolation_paper_trading_sell_does_not_affect_portfolio(mock_db, mock_market):
    """
    Verify that paper trading SELL orders do not query or modify portfolio table.
    """
    # Arrange
    paper_position = Position(ticker="TSLA", quantity=30.0, buy_price=600.0, current_price=700.0)
    mock_db.fetch_positions.return_value = [paper_position]
    
    trading_service = TradingService(db=mock_db, market=mock_market)
    order = Order(
        ticker="TSLA",
        action="SELL",
        quantity=15.0,
        price=720.0,
        timestamp=datetime.now()
    )
    
    # Act
    result = trading_service.execute_order(user_id="test_user", order=order, cash_balance=10000.0)
    
    # Assert
    assert result["status"] == "SUCCESS"
    
    # Verify fetch_positions was called with paper_portfolio table
    fetch_call = mock_db.fetch_positions.call_args
    assert fetch_call[0][0] == "test_user"
    assert fetch_call[1]["table_name"] == "paper_portfolio"
    
    # Verify no calls were made to portfolio table
    for call_obj in mock_db.fetch_positions.call_args_list:
        if len(call_obj[1]) > 0 and "table_name" in call_obj[1]:
            assert call_obj[1]["table_name"] != "portfolio", \
                "Paper trading must not access portfolio table"
