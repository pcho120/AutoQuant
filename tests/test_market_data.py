import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from adapters.market_data import MarketDataAdapter


@pytest.fixture
def market_adapter():
    """Create market data adapter."""
    return MarketDataAdapter(max_workers=2)


def test_fetch_current_prices_success(market_adapter):
    """Test fetching current prices for multiple tickers successfully."""
    # Mock yfinance Ticker objects
    with patch('adapters.market_data.yf.Ticker') as mock_ticker:
        # Create mock history dataframes
        mock_aapl_hist = pd.DataFrame({'Close': [150.0, 155.0, 160.0]})
        mock_msft_hist = pd.DataFrame({'Close': [300.0, 310.0, 320.0]})
        
        def ticker_side_effect(symbol):
            mock = Mock()
            if symbol == "AAPL":
                mock.history.return_value = mock_aapl_hist
            elif symbol == "MSFT":
                mock.history.return_value = mock_msft_hist
            return mock
        
        mock_ticker.side_effect = ticker_side_effect
        
        prices = market_adapter.fetch_current_prices(["AAPL", "MSFT"])
        
        assert "AAPL" in prices
        assert "MSFT" in prices
        assert prices["AAPL"] == 160.0
        assert prices["MSFT"] == 320.0


def test_fetch_current_prices_with_failures(market_adapter):
    """Test fetching prices handles failures gracefully."""
    with patch('adapters.market_data.yf.Ticker') as mock_ticker:
        # Create mock for AAPL (success) and FAIL (failure)
        def ticker_side_effect(symbol):
            mock = Mock()
            if symbol == "AAPL":
                mock.history.return_value = pd.DataFrame({'Close': [150.0]})
            else:
                # Simulate failure with empty dataframe
                mock.history.return_value = pd.DataFrame()
            return mock
        
        mock_ticker.side_effect = ticker_side_effect
        
        prices = market_adapter.fetch_current_prices(["AAPL", "FAIL"])
        
        # Only successful ticker should be in result
        assert "AAPL" in prices
        assert "FAIL" not in prices
        assert prices["AAPL"] == 150.0


def test_fetch_historical_data(market_adapter):
    """Test fetching historical data for a single ticker."""
    with patch('adapters.market_data.yf.Ticker') as mock_ticker:
        # Create mock historical data
        mock_hist = pd.DataFrame({
            'Open': [145.0, 148.0, 150.0],
            'High': [147.0, 152.0, 155.0],
            'Low': [144.0, 147.0, 149.0],
            'Close': [146.0, 150.0, 154.0],
            'Volume': [1000000, 1200000, 1100000]
        })
        
        mock_ticker_obj = Mock()
        mock_ticker_obj.history.return_value = mock_hist
        mock_ticker.return_value = mock_ticker_obj
        
        result = market_adapter.fetch_historical_data(ticker="AAPL", period="1mo", interval="1d")
        
        assert not result.empty
        assert len(result) == 3
        assert "Close" in result.columns
        assert result["Close"].iloc[-1] == 154.0
        
        # Verify yfinance was called with correct parameters
        mock_ticker_obj.history.assert_called_once_with(period="1mo", interval="1d")


def test_fetch_ticker_info(market_adapter):
    """Test fetching ticker metadata."""
    with patch('adapters.market_data.yf.Ticker') as mock_ticker:
        # Create mock ticker info
        mock_info = {
            'symbol': 'AAPL',
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'marketCap': 2500000000000
        }
        
        mock_ticker_obj = Mock()
        mock_ticker_obj.info = mock_info
        mock_ticker.return_value = mock_ticker_obj
        
        result = market_adapter.fetch_ticker_info(ticker="AAPL")
        
        assert result == mock_info
        assert result['symbol'] == 'AAPL'
        assert result['sector'] == 'Technology'
