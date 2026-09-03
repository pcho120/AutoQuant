import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / "secrets.env")


class CollectionRepository:
    """Supabase persistence for collection and scheduled prediction pipelines."""

    def __init__(self, client: Client | None = None):
        if client is not None:
            self.client = client
            return
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials not found in environment variables")
        self.client = create_client(url, key)

    def upsert_market_prices(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        self.client.table("market_prices").upsert(
            rows,
            on_conflict="ticker,timestamp",
        ).execute()
        return len(rows)

    def fetch_market_prices(
        self,
        tickers: tuple[str, ...],
        timeframe: str = "1d",
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = (
                self.client.table("market_prices")
                .select("ticker,timestamp,open,high,low,close,volume,timeframe")
                .in_("ticker", list(tickers))
                .eq("timeframe", timeframe)
                .order("timestamp")
                .range(offset, offset + page_size - 1)
                .execute()
            )
            page = response.data or []
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def upsert_news_articles(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        with_url = [row for row in rows if row.get("url")]
        without_url = [row for row in rows if not row.get("url")]
        if with_url:
            self.client.table("news_articles").upsert(
                with_url,
                on_conflict="ticker,url",
                ignore_duplicates=True,
            ).execute()
        if without_url:
            self.client.table("news_articles").upsert(
                without_url,
                on_conflict="ticker,provider_article_id",
                ignore_duplicates=True,
            ).execute()
        return len(rows)

    def fetch_unprocessed_news(self, limit: int) -> list[dict[str, Any]]:
        response = (
            self.client.table("news_articles")
            .select("id,ticker,published_at,source,title,description,url,author,collected_at")
            .is_("analyzed_at", "null")
            .order("published_at")
            .limit(limit)
            .execute()
        )
        return response.data or []

    def update_news_analysis(self, article_id: int, analysis: dict[str, Any]) -> None:
        (
            self.client.table("news_articles")
            .update(analysis)
            .eq("id", article_id)
            .is_("analyzed_at", "null")
            .execute()
        )

    def upsert_prediction_features(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        self.client.table("prediction_features").upsert(
            rows,
            on_conflict="ticker,timestamp,feature_version",
        ).execute()
        return len(rows)

    def upsert_predictions(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        self.client.table("predictions").upsert(
            rows,
            on_conflict="ticker,prediction_timestamp,horizon,model_version",
        ).execute()
        return len(rows)

    def upsert_model_evaluation(self, row: dict[str, Any]) -> None:
        self.client.table("model_evaluations").upsert(
            row,
            on_conflict="model_version,test_start,test_end",
        ).execute()

    def upsert_model_artifact(self, row: dict[str, Any]) -> None:
        self.client.table("model_registry").upsert(
            row,
            on_conflict="model_version",
        ).execute()

    def fetch_prediction_features(self, feature_version: str, page_size: int = 1000) -> list[dict[str, Any]]:
        return self._fetch_pages(
            "prediction_features",
            "*",
            filters=(("feature_version", feature_version),),
            order="timestamp",
            page_size=page_size,
        )

    def fetch_latest_model_artifact(self, horizon: str) -> dict[str, Any] | None:
        response = (
            self.client.table("model_registry")
            .select("*")
            .eq("horizon", horizon)
            .order("trained_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def fetch_latest_predictions(self, horizon: str, limit: int = 500) -> list[dict[str, Any]]:
        response = (
            self.client.table("predictions")
            .select("*")
            .eq("horizon", horizon)
            .order("prediction_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        latest: dict[str, dict[str, Any]] = {}
        for row in response.data or []:
            latest.setdefault(row["ticker"], row)
        return list(latest.values())

    def fetch_latest_prediction(self, ticker: str, horizon: str) -> dict[str, Any] | None:
        response = (
            self.client.table("predictions")
            .select("*")
            .eq("ticker", ticker.upper())
            .eq("horizon", horizon)
            .order("prediction_timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return rows[0] if rows else None

    def fetch_recent_news(
        self,
        ticker: str,
        published_before: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        query = (
            self.client.table("news_articles")
            .select("published_at,source,title,url,sentiment,event_type,materiality,impact,impact_horizon")
            .eq("ticker", ticker.upper())
            .not_.is_("analyzed_at", "null")
        )
        if published_before:
            query = query.lte("published_at", published_before)
        response = query.order("published_at", desc=True).limit(limit).execute()
        return response.data or []

    def _fetch_pages(
        self,
        table: str,
        columns: str,
        filters: tuple[tuple[str, Any], ...] = (),
        order: str | None = None,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = self.client.table(table).select(columns)
            for column, value in filters:
                query = query.eq(column, value)
            if order:
                query = query.order(order)
            response = query.range(offset, offset + page_size - 1).execute()
            page = response.data or []
            rows.extend(page)
            if len(page) < page_size:
                return rows
            offset += page_size