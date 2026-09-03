from datetime import datetime, timezone
import logging

from adapters.collection_repository import CollectionRepository
from adapters.news_provider import NewsProvider
from services.retry import retry_call


logger = logging.getLogger(__name__)
ANALYSIS_VERSION = "keyword-structured-v1.0.0"

EVENT_KEYWORDS = {
    "earnings": ("earnings", "revenue", "eps", "quarterly results", "guidance"),
    "merger_acquisition": ("acquisition", "acquire", "merger", "takeover"),
    "regulatory": ("sec", "regulator", "antitrust", "investigation", "approval"),
    "product": ("launch", "product", "platform", "release"),
    "analyst_rating": ("upgrade", "downgrade", "price target", "outperform", "underperform"),
    "management": ("ceo", "cfo", "executive", "resign", "appointed"),
    "litigation": ("lawsuit", "court", "settlement", "legal"),
}

MATERIAL_TERMS = (
    "earnings", "guidance", "merger", "acquisition", "investigation", "approval",
    "bankruptcy", "lawsuit", "ceo", "downgrade", "upgrade",
)


class NewsAnalyzer:
    """Analyze persisted articles without fetching the news provider again."""

    def __init__(self, repository: CollectionRepository, sentiment_provider: NewsProvider):
        self.repository = repository
        self.sentiment_provider = sentiment_provider

    def analyze_unprocessed(
        self,
        limit: int,
        retry_attempts: int = 3,
        retry_base_delay_seconds: float = 1.0,
    ) -> dict[str, int]:
        summary = {"articles_analyzed": 0, "articles_failed": 0}
        articles = retry_call(
            lambda: self.repository.fetch_unprocessed_news(limit),
            attempts=retry_attempts,
            base_delay_seconds=retry_base_delay_seconds,
        )
        for article in articles:
            try:
                analysis = self.analyze(article)
                retry_call(
                    lambda: self.repository.update_news_analysis(article["id"], analysis),
                    attempts=retry_attempts,
                    base_delay_seconds=retry_base_delay_seconds,
                )
                summary["articles_analyzed"] += 1
            except Exception:
                summary["articles_failed"] += 1
                logger.exception("News analysis failed for article %s", article.get("id"))
        return summary

    def analyze(self, article: dict) -> dict:
        text = f"{article.get('title') or ''} {article.get('description') or ''}".lower()
        sentiment = self.sentiment_provider.get_sentiment(article)
        event_type = next((event for event, terms in EVENT_KEYWORDS.items() if any(term in text for term in terms)), "other")
        material_hits = sum(term in text for term in MATERIAL_TERMS)
        materiality = min(1.0, 0.25 + material_hits * 0.25)
        impact = "positive" if sentiment > 0.15 else "negative" if sentiment < -0.15 else "neutral"
        impact_horizon = {
            "earnings": "1-20d",
            "merger_acquisition": "20d+",
            "regulatory": "5-20d",
            "product": "5-20d",
            "analyst_rating": "1-5d",
            "management": "5-20d",
            "litigation": "20d+",
        }.get(event_type, "1-5d")
        return {
            "sentiment": sentiment,
            "event_type": event_type,
            "materiality": materiality,
            "impact": impact,
            "impact_horizon": impact_horizon,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "analysis_version": ANALYSIS_VERSION,
        }