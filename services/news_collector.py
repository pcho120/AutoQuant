from datetime import datetime, timezone
import hashlib
import logging

from adapters.collection_repository import CollectionRepository
from adapters.news_provider import NewsProvider
from services.collection_config import CollectionConfig
from services.retry import retry_call


logger = logging.getLogger(__name__)


class NewsCollector:
    def __init__(
        self,
        news: NewsProvider,
        repository: CollectionRepository,
        config: CollectionConfig,
    ):
        self.news = news
        self.repository = repository
        self.config = config

    def collect(self, tickers: tuple[str, ...] | None = None) -> dict[str, int]:
        summary = {"tickers_succeeded": 0, "tickers_failed": 0, "rows_upserted": 0}
        collected_at = datetime.now(timezone.utc).isoformat()
        for ticker in tickers or self.config.tickers:
            try:
                articles = retry_call(
                    lambda ticker=ticker: self.news.fetch_news(
                        ticker,
                        days=self.config.news_lookback_days,
                    ),
                    attempts=self.config.retry_attempts,
                    base_delay_seconds=self.config.retry_base_delay_seconds,
                )
                rows = [self._to_row(ticker, article, collected_at) for article in articles]
                summary["rows_upserted"] += retry_call(
                    lambda: self.repository.upsert_news_articles(rows),
                    attempts=self.config.retry_attempts,
                    base_delay_seconds=self.config.retry_base_delay_seconds,
                )
                summary["tickers_succeeded"] += 1
            except Exception:
                summary["tickers_failed"] += 1
                logger.exception("News collection failed for %s", ticker)
        return summary

    @staticmethod
    def _to_row(ticker: str, article: dict, collected_at: str) -> dict:
        source = article.get("source") or {}
        source_name = source.get("name") if isinstance(source, dict) else str(source)
        identity = article.get("url") or "|".join([
            source_name or "",
            article.get("title") or "",
            article.get("publishedAt") or "",
        ])
        provider_article_id = "newsapi:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return {
            "ticker": ticker.upper(),
            "published_at": article.get("publishedAt"),
            "source": source_name,
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "author": article.get("author"),
            "provider_article_id": provider_article_id,
            "collected_at": collected_at,
        }