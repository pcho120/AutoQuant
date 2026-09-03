from datetime import timezone
import logging
import math

import pandas as pd

from adapters.collection_repository import CollectionRepository
from adapters.market_data import MarketDataAdapter
from services.collection_config import CollectionConfig
from services.retry import retry_call


logger = logging.getLogger(__name__)


class MarketDataCollector:
    def __init__(
        self,
        market: MarketDataAdapter,
        repository: CollectionRepository,
        config: CollectionConfig,
    ):
        self.market = market
        self.repository = repository
        self.config = config

    def collect(self, tickers: tuple[str, ...] | None = None) -> dict[str, int]:
        summary = {"tickers_succeeded": 0, "tickers_failed": 0, "rows_upserted": 0}
        for ticker in tickers or self.config.tickers:
            try:
                history = retry_call(
                    lambda ticker=ticker: self.market.fetch_historical_data(
                        ticker,
                        period=self.config.market_period,
                        interval=self.config.market_interval,
                    ),
                    attempts=self.config.retry_attempts,
                    base_delay_seconds=self.config.retry_base_delay_seconds,
                )
                rows = self._to_rows(ticker, history, self.config.market_interval)
                summary["rows_upserted"] += retry_call(
                    lambda: self.repository.upsert_market_prices(rows),
                    attempts=self.config.retry_attempts,
                    base_delay_seconds=self.config.retry_base_delay_seconds,
                )
                summary["tickers_succeeded"] += 1
            except Exception:
                summary["tickers_failed"] += 1
                logger.exception("Market data collection failed for %s", ticker)
        return summary

    @staticmethod
    def _to_rows(ticker: str, history: pd.DataFrame, timeframe: str = "1d") -> list[dict]:
        if history is None or history.empty:
            raise ValueError(f"No market data returned for {ticker}")
        data = history.copy()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(data.columns):
            raise ValueError(f"Market data is missing OHLCV columns for {ticker}")

        rows = []
        for timestamp, candle in data.iterrows():
            parsed_timestamp = pd.Timestamp(timestamp)
            if parsed_timestamp.tzinfo is None:
                parsed_timestamp = parsed_timestamp.tz_localize(timezone.utc)
            else:
                parsed_timestamp = parsed_timestamp.tz_convert(timezone.utc)
            values = [candle["Open"], candle["High"], candle["Low"], candle["Close"], candle["Volume"]]
            if any(pd.isna(value) or not math.isfinite(float(value)) for value in values):
                continue
            rows.append({
                "ticker": ticker.upper(),
                "timestamp": parsed_timestamp.isoformat(),
                "open": float(candle["Open"]),
                "high": float(candle["High"]),
                "low": float(candle["Low"]),
                "close": float(candle["Close"]),
                "volume": int(candle["Volume"]),
                "source": "yfinance",
                "timeframe": timeframe,
            })
        return rows