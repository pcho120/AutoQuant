from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PredictionRequest:
    """Request object for stock price prediction."""
    ticker: str
    horizon: str
    include_news: bool = False
    include_indicators: bool = False


@dataclass
class PredictionResult:
    """Result object for stock price prediction."""
    ticker: str
    current_price: float
    predicted_price: float
    confidence: float
    reasoning: str
    chart_data: Optional[dict] = field(default=None)

    @property
    def change_dollars(self) -> float:
        """Calculate absolute price change in dollars."""
        return self.predicted_price - self.current_price

    @property
    def change_percent(self) -> float:
        """Calculate percentage price change.
        
        Returns 0.0 if current_price is 0 to avoid division by zero.
        """
        if self.current_price == 0:
            return 0.0
        return (self.change_dollars / self.current_price) * 100
