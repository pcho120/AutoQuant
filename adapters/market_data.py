from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time, timezone
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd


class MarketDataAdapter:
    """Adapter for fetching market data using yfinance with parallel execution."""

    def __init__(self, max_workers: int = 10, request_timeout: float = 15.0):
        """
        Initialize the adapter with a thread pool.

        Args:
            max_workers: Maximum number of threads for parallel execution
        """
        self.max_workers = max_workers
        self.request_timeout = request_timeout

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
                hist = ticker_obj.history(period="1d", timeout=self.request_timeout)
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

    def fetch_trade_quote(self, ticker: str) -> dict:
        """Return the latest regular-session one-minute quote for simulated execution."""
        history = yf.Ticker(ticker).history(
            period="5d",
            interval="1m",
            prepost=False,
            timeout=self.request_timeout,
        )
        if history.empty or "Close" not in history:
            raise ValueError(f"No trade quote is available for {ticker}")

        timestamp = pd.Timestamp(history.index[-1])
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        timestamp = timestamp.tz_convert("UTC")
        now = datetime.now(timezone.utc)
        age_seconds = (now - timestamp.to_pydatetime()).total_seconds()
        eastern_now = now.astimezone(ZoneInfo("America/New_York"))
        regular_session = (
            eastern_now.weekday() < 5
            and time(9, 30) <= eastern_now.time().replace(tzinfo=None) < time(16, 0)
        )
        quote_fresh = -60 <= age_seconds <= 1800
        closing_price_available = 0 <= age_seconds <= 7 * 24 * 60 * 60
        return {
            "ticker": ticker.upper(),
            "price": float(history["Close"].iloc[-1]),
            "timestamp": timestamp.isoformat(),
            "marketOpen": regular_session and quote_fresh,
            "regularSession": regular_session,
            "afterHoursBuyAllowed": not regular_session and closing_price_available,
            "availableQuantity": max(0.0, float(history["Volume"].iloc[-1]) * 0.01)
            if "Volume" in history else 0.0,
        }

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
        return ticker_obj.history(period=period, interval=interval, timeout=self.request_timeout)

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

    def search_tickers(self, query: str) -> list[dict[str, str]]:
        """Search Yahoo Finance for supported market symbols."""
        supported_types = {
            "CRYPTOCURRENCY", "CURRENCY", "EQUITY", "ETF", "FUTURE", "INDEX", "MUTUALFUND",
        }
        quotes = yf.Search(query.strip(), max_results=15).quotes
        results = []
        seen = set()
        for quote in quotes:
            symbol = quote.get("symbol", "").upper()
            if not symbol or symbol in seen or quote.get("quoteType", "").upper() not in supported_types:
                continue
            results.append({
                "ticker": symbol,
                "name": quote.get("shortname") or quote.get("longname") or symbol,
            })
            seen.add(symbol)
        return results
