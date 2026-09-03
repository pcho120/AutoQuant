from dataclasses import dataclass
import os


DEFAULT_TICKERS = (
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ", "^VIX",
    "XLK", "XLC", "XLY", "XLF", "XLE", "XLV",
)


@dataclass(frozen=True)
class CollectionConfig:
    tickers: tuple[str, ...]
    market_period: str
    market_interval: str
    news_lookback_days: int
    retry_attempts: int
    retry_base_delay_seconds: float
    request_timeout_seconds: float
    analysis_batch_size: int

    @classmethod
    def from_env(cls) -> "CollectionConfig":
        configured_tickers = os.getenv("COLLECTION_TICKERS", "")
        tickers = tuple(
            dict.fromkeys(ticker.strip().upper() for ticker in configured_tickers.split(",") if ticker.strip())
        ) or DEFAULT_TICKERS
        return cls(
            tickers=tickers,
            market_period=os.getenv("MARKET_COLLECTION_PERIOD", "10y"),
            market_interval=os.getenv("MARKET_COLLECTION_INTERVAL", "1d"),
            news_lookback_days=int(os.getenv("NEWS_COLLECTION_LOOKBACK_DAYS", "2")),
            retry_attempts=max(1, int(os.getenv("COLLECTION_RETRY_ATTEMPTS", "3"))),
            retry_base_delay_seconds=max(0.0, float(os.getenv("COLLECTION_RETRY_BASE_DELAY_SECONDS", "1"))),
            request_timeout_seconds=max(1.0, float(os.getenv("COLLECTION_REQUEST_TIMEOUT_SECONDS", "15"))),
            analysis_batch_size=max(1, int(os.getenv("NEWS_ANALYSIS_BATCH_SIZE", "100"))),
        )