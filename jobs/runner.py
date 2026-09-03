import argparse
import json
import logging
import os

from adapters.collection_repository import CollectionRepository
from adapters.market_data import MarketDataAdapter
from adapters.news_provider import NewsProvider
from services.collection_config import CollectionConfig
from services.market_data_collector import MarketDataCollector
from services.news_analyzer import NewsAnalyzer
from services.news_collector import NewsCollector
from services.prediction_pipeline import PredictionPipeline


logger = logging.getLogger(__name__)


def collect_market_data(config: CollectionConfig, repository: CollectionRepository) -> dict[str, int]:
    market = MarketDataAdapter(request_timeout=config.request_timeout_seconds)
    return MarketDataCollector(market, repository, config).collect()


def collect_news(config: CollectionConfig, repository: CollectionRepository) -> dict[str, int]:
    news = NewsProvider(
        os.getenv("NEWS_API_KEY", ""),
        request_timeout=config.request_timeout_seconds,
        raise_on_error=True,
    )
    if not news.api_key:
        raise ValueError("NEWS_API_KEY is required for news collection")
    return NewsCollector(news, repository, config).collect()


def analyze_unprocessed_news(config: CollectionConfig, repository: CollectionRepository) -> dict[str, int]:
    analyzer = NewsAnalyzer(repository, NewsProvider(""))
    return analyzer.analyze_unprocessed(
        config.analysis_batch_size,
        retry_attempts=config.retry_attempts,
        retry_base_delay_seconds=config.retry_base_delay_seconds,
    )


def build_prediction_features(config: CollectionConfig, repository: CollectionRepository) -> dict:
    return PredictionPipeline(repository, config).build_features()


def run_model_evaluation(config: CollectionConfig, repository: CollectionRepository) -> dict:
    return PredictionPipeline(repository, config).evaluate_model()


def run_predictions(config: CollectionConfig, repository: CollectionRepository) -> dict:
    return PredictionPipeline(repository, config).run_predictions()


JOBS = {
    "collect_market_data": collect_market_data,
    "collect_news": collect_news,
    "analyze_unprocessed_news": analyze_unprocessed_news,
    "build_prediction_features": build_prediction_features,
    "run_model_evaluation": run_model_evaluation,
    "run_predictions": run_predictions,
}


def job_failed(summary: dict) -> bool:
    if summary.get("status") and summary["status"] != "validated":
        return True
    return any(
        isinstance(value, int) and key.endswith("_failed") and value > 0
        for key, value in summary.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one AutoQuant scheduled data or prediction job")
    parser.add_argument("job", choices=JOBS)
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        summary = JOBS[args.job](CollectionConfig.from_env(), CollectionRepository())
    except Exception:
        logger.exception("Job %s failed before completion", args.job)
        return 1
    logger.info("Job %s completed: %s", args.job, json.dumps(summary, sort_keys=True))
    return 1 if job_failed(summary) else 0


if __name__ == "__main__":
    raise SystemExit(main())