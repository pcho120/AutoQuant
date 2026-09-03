from typing import Any

__all__ = ["PortfolioService", "PredictionService", "TradingService"]


def __getattr__(name: str) -> Any:
	if name == "PortfolioService":
		from services.portfolio_service import PortfolioService
		return PortfolioService
	if name == "PredictionService":
		from services.prediction_service import PredictionService
		return PredictionService
	if name == "TradingService":
		from services.trading_service import TradingService
		return TradingService
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
