from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd

from adapters.collection_repository import CollectionRepository
from adapters.news_provider import NewsProvider
from services.collection_config import CollectionConfig
from services.market_data_collector import MarketDataCollector
from services.news_analyzer import NewsAnalyzer
from services.news_collector import NewsCollector
from services.retry import retry_call


def config() -> CollectionConfig:
    return CollectionConfig(
        tickers=("FAIL", "AAPL"),
        market_period="5d",
        market_interval="15m",
        news_lookback_days=2,
        retry_attempts=1,
        retry_base_delay_seconds=0,
        request_timeout_seconds=5,
        analysis_batch_size=10,
    )


class FakeSupabase:
    def __init__(self):
        self.rows = {
            "market_prices": [],
            "news_articles": [],
            "prediction_features": [],
            "predictions": [],
            "model_evaluations": [],
            "model_registry": [],
        }

    def table(self, name):
        return FakeQuery(self, name)


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.operation = "select"
        self.payload = None
        self.conflict = None
        self.ignore_duplicates = False
        self.filters = []
        self.limit_count = None

    def upsert(self, rows, on_conflict, ignore_duplicates=False):
        self.operation = "upsert"
        self.payload = rows
        self.conflict = on_conflict.split(",")
        self.ignore_duplicates = ignore_duplicates
        return self

    def select(self, _columns):
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def is_(self, column, value):
        self.filters.append((column, None if value == "null" else value))
        return self

    def order(self, _column):
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def execute(self):
        table_rows = self.client.rows[self.table]
        if self.operation == "upsert":
            for incoming in self.payload:
                existing = next((
                    row for row in table_rows
                    if all(row.get(key) == incoming.get(key) for key in self.conflict)
                ), None)
                if existing:
                    if not self.ignore_duplicates:
                        existing.update(incoming)
                else:
                    table_rows.append({"id": len(table_rows) + 1, **incoming})
            return SimpleNamespace(data=self.payload)
        matching = [row for row in table_rows if all(row.get(key) == value for key, value in self.filters)]
        if self.operation == "update":
            for row in matching:
                row.update(self.payload)
            return SimpleNamespace(data=matching)
        return SimpleNamespace(data=matching[:self.limit_count] if self.limit_count else matching)


class StaticMarket:
    def __init__(self, history):
        self.history = history

    def fetch_historical_data(self, ticker, period, interval):
        if ticker == "FAIL":
            raise ConnectionError("rate limited")
        return self.history


class StaticNews:
    def __init__(self, articles):
        self.articles = articles

    def fetch_news(self, ticker, days):
        return self.articles


class FailingNews:
    def fetch_news(self, ticker, days):
        raise ConnectionError("NewsAPI unavailable")


def market_history():
    index = pd.DatetimeIndex([
        pd.Timestamp("2026-08-27 09:30", tz=ZoneInfo("America/New_York")),
    ])
    return pd.DataFrame({
        "Open": [100.0], "High": [102.0], "Low": [99.0], "Close": [101.0], "Volume": [1000],
    }, index=index)


def test_same_market_candle_is_upserted_without_duplicate():
    client = FakeSupabase()
    collector = MarketDataCollector(StaticMarket(market_history()), CollectionRepository(client), config())

    collector.collect(("AAPL",))
    collector.collect(("AAPL",))

    assert len(client.rows["market_prices"]) == 1
    assert client.rows["market_prices"][0]["timestamp"] == "2026-08-27T13:30:00+00:00"


def test_same_news_article_is_upserted_without_duplicate():
    client = FakeSupabase()
    article = {
        "source": {"name": "Example Wire"},
        "author": "Reporter",
        "title": "AAPL reports earnings growth",
        "description": "Revenue beat expectations",
        "url": "https://example.com/aapl-earnings",
        "publishedAt": "2026-08-27T12:00:00Z",
    }
    collector = NewsCollector(StaticNews([article]), CollectionRepository(client), config())

    collector.collect(("AAPL",))
    collector.collect(("AAPL",))

    assert len(client.rows["news_articles"]) == 1
    assert client.rows["news_articles"][0]["provider_article_id"].startswith("newsapi:")
    assert client.rows["news_articles"][0]["published_at"] == "2026-08-27T12:00:00Z"
    collected_at = datetime.fromisoformat(client.rows["news_articles"][0]["collected_at"])
    assert collected_at.utcoffset() == timedelta(0)


def test_same_news_article_can_be_associated_with_multiple_tickers():
    client = FakeSupabase()
    article = {
        "source": {"name": "Example Wire"},
        "title": "Technology stocks rally",
        "url": "https://example.com/technology-rally",
        "publishedAt": "2026-08-27T12:00:00Z",
    }
    collector = NewsCollector(StaticNews([article]), CollectionRepository(client), config())

    collector.collect(("AAPL", "NVDA"))

    assert [row["ticker"] for row in client.rows["news_articles"]] == ["AAPL", "NVDA"]


def test_analyzed_news_is_not_analyzed_again():
    client = FakeSupabase()
    client.rows["news_articles"].append({
        "id": 1,
        "ticker": "AAPL",
        "title": "AAPL earnings beat estimates",
        "description": "Strong growth and upgraded guidance",
        "published_at": "2026-08-27T12:00:00Z",
        "analyzed_at": None,
    })
    analyzer = NewsAnalyzer(CollectionRepository(client), NewsProvider(""))

    first = analyzer.analyze_unprocessed(10)
    second = analyzer.analyze_unprocessed(10)

    assert first == {"articles_analyzed": 1, "articles_failed": 0}
    assert second == {"articles_analyzed": 0, "articles_failed": 0}
    assert client.rows["news_articles"][0]["event_type"] == "earnings"


def test_news_analysis_accepts_null_article_text():
    analyzer = NewsAnalyzer(CollectionRepository(FakeSupabase()), NewsProvider(""))

    analysis = analyzer.analyze({"title": "AAPL earnings beat estimates", "description": None})

    assert analysis["sentiment"] == 1.0
    assert analysis["event_type"] == "earnings"


def test_market_failure_does_not_prevent_next_ticker():
    client = FakeSupabase()
    collector = MarketDataCollector(StaticMarket(market_history()), CollectionRepository(client), config())

    result = collector.collect()

    assert result == {"tickers_succeeded": 1, "tickers_failed": 1, "rows_upserted": 1}
    assert client.rows["market_prices"][0]["ticker"] == "AAPL"


def test_news_api_failure_does_not_block_analysis_job():
    client = FakeSupabase()
    client.rows["news_articles"].append({
        "id": 1,
        "ticker": "MSFT",
        "title": "MSFT product launch",
        "description": "New platform release",
        "published_at": "2026-08-27T12:00:00Z",
        "analyzed_at": None,
    })
    repository = CollectionRepository(client)

    collection = NewsCollector(FailingNews(), repository, config()).collect(("AAPL",))
    analysis = NewsAnalyzer(repository, NewsProvider("")).analyze_unprocessed(10)

    assert collection == {"tickers_succeeded": 0, "tickers_failed": 1, "rows_upserted": 0}
    assert analysis == {"articles_analyzed": 1, "articles_failed": 0}


def test_retry_call_retries_transient_failure():
    attempts = []

    def flaky_operation():
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("temporary failure")
        return "completed"

    assert retry_call(flaky_operation, attempts=2, base_delay_seconds=0) == "completed"
    assert len(attempts) == 2


def test_prediction_snapshots_are_idempotent_per_version():
    client = FakeSupabase()
    repository = CollectionRepository(client)
    feature = {
        "ticker": "AAPL",
        "timestamp": "2026-08-27T20:00:00+00:00",
        "feature_version": "features-v1.0.0",
        "rsi_14": 55.0,
    }
    prediction = {
        "ticker": "AAPL",
        "prediction_timestamp": "2026-08-27T20:00:00+00:00",
        "horizon": "5d",
        "model_version": "prediction-v1.0.0",
        "current_price": 100.0,
        "signal": "HOLD",
    }

    repository.upsert_prediction_features([feature])
    repository.upsert_prediction_features([{**feature, "rsi_14": 56.0}])
    repository.upsert_predictions([prediction])
    repository.upsert_predictions([{**prediction, "signal": "BUY"}])

    assert len(client.rows["prediction_features"]) == 1
    assert client.rows["prediction_features"][0]["rsi_14"] == 56.0
    assert len(client.rows["predictions"]) == 1
    assert client.rows["predictions"][0]["signal"] == "BUY"