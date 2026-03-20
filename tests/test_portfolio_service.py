import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
from services.portfolio_service import PortfolioService
from domain.position import Position, Portfolio
from domain.ticker import Ticker, Sector, RiskLevel


@pytest.fixture
def mock_db():
    """Mock database adapter."""
    return Mock()


@pytest.fixture
def mock_market():
    """Mock market data adapter."""
    return Mock()


@pytest.fixture
def portfolio_service(mock_db, mock_market):
    """Create portfolio service with mocked dependencies."""
    return PortfolioService(db=mock_db, market=mock_market)


def test_label_risk_tech_sector():
    """Test that tech sector is labeled as HIGH risk."""
    service = PortfolioService(db=Mock(), market=Mock())
    ticker = Ticker(symbol="AAPL", sector=Sector.TECH, risk_level=RiskLevel.MEDIUM)
    
    risk = service.label_risk(ticker)
    
    assert risk == RiskLevel.HIGH


def test_label_risk_utilities_sector():
    """Test that utilities sector is labeled as MEDIUM risk."""
    service = PortfolioService(db=Mock(), market=Mock())
    ticker = Ticker(symbol="NEE", sector=Sector.UTILITIES, risk_level=RiskLevel.LOW)
    
    risk = service.label_risk(ticker)
    
    assert risk == RiskLevel.MEDIUM


def test_label_risk_unknown_sector():
    """Test that unknown sector defaults to MEDIUM risk."""
    service = PortfolioService(db=Mock(), market=Mock())
    ticker = Ticker(symbol="XYZ", sector=Sector.UNKNOWN, risk_level=RiskLevel.LOW)
    
    risk = service.label_risk(ticker)
    
    assert risk == RiskLevel.MEDIUM


def test_calculate_allocation_basic():
    """Test portfolio allocation calculation with multiple positions."""
    service = PortfolioService(db=Mock(), market=Mock())
    
    positions = [
        Position(ticker="AAPL", quantity=10, buy_price=150.0, current_price=160.0),
        Position(ticker="MSFT", quantity=5, buy_price=300.0, current_price=320.0),
    ]
    portfolio = Portfolio(positions=positions, cash=5000.0)
    
    allocation = service.calculate_allocation(portfolio)
    
    # AAPL: 10 * 160 = 1600
    # MSFT: 5 * 320 = 1600
    # Total value: 1600 + 1600 + 5000 = 8200
    # AAPL allocation: (1600 / 8200) * 100 = 19.51%
    # MSFT allocation: (1600 / 8200) * 100 = 19.51%
    
    assert "AAPL" in allocation
    assert "MSFT" in allocation
    assert abs(allocation["AAPL"] - 19.51) < 0.1
    assert abs(allocation["MSFT"] - 19.51) < 0.1


def test_calculate_allocation_empty_portfolio():
    """Test allocation calculation returns empty dict for zero invested value."""
    service = PortfolioService(db=Mock(), market=Mock())
    
    portfolio = Portfolio(positions=[], cash=10000.0)
    
    allocation = service.calculate_allocation(portfolio)
    
    assert allocation == {}


def test_update_positions(mock_db):
    """Test updating positions from DataFrame."""
    service = PortfolioService(db=mock_db, market=Mock())
    
    # Create mock DataFrame
    data = {
        "Ticker": ["AAPL", "MSFT"],
        "Quantity": [10.0, 5.0],
        "Buy Price": [150.0, 300.0],
        "Current Price": [160.0, 320.0]
    }
    df = pd.DataFrame(data)
    
    result = service.update_positions(user_id="user123", edited_df=df)
    
    assert result is True
    mock_db.save_positions.assert_called_once()
    
    # Verify the positions passed to save_positions
    call_args = mock_db.save_positions.call_args
    assert call_args[0][0] == "user123"
    positions = call_args[0][1]
    assert len(positions) == 2
    assert positions[0].ticker == "AAPL"
    assert positions[1].ticker == "MSFT"
