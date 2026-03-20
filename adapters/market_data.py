from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import yfinance as yf
import pandas as pd


class MarketDataAdapter:
    """Adapter for fetching market data using yfinance with parallel execution."""

    def __init__(self, max_workers: int = 10):
        """
        Initialize the adapter with a thread pool.

        Args:
            max_workers: Maximum number of threads for parallel execution
        """
        self.max_workers = max_workers

    def fetch_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch current prices for multiple tickers in parallel.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker symbols to their current prices.
            Failed tickers are omitted from the result.
        """
        prices = {}

        def fetch_single_price(ticker: str) -> tuple[str, Optional[float]]:
            """Fetch price for a single ticker, return (ticker, price or None)."""
            try:
                ticker_obj = yf.Ticker(ticker)
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    return (ticker, float(hist["Close"].iloc[-1]))
                return (ticker, None)
            except Exception:
                return (ticker, None)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fetch_single_price, ticker): ticker for ticker in tickers}

            for future in as_completed(futures):
                ticker, price = future.result()
                if price is not None:
                    prices[ticker] = price

        return prices

    def fetch_historical_data(
        self, ticker: str, period: str = "1mo", interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical data for a single ticker.

        Args:
            ticker: Ticker symbol
            period: Time period (e.g., '1d', '5d', '1mo', '1y')
            interval: Data interval (e.g., '1m', '5m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data
        """
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.history(period=period, interval=interval)

    def fetch_ticker_info(self, ticker: str) -> dict:
        """
        Fetch ticker information/metadata.

        Args:
            ticker: Ticker symbol

        Returns:
            Dictionary containing ticker metadata
        """
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.info
