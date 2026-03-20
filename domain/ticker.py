from dataclasses import dataclass
from enum import Enum


class Sector(str, Enum):
    """Sector classification for stocks."""
    TECH = "Technology"
    FINANCE = "Finance"
    HEALTHCARE = "Healthcare"
    ENERGY = "Energy"
    CONSUMER = "Consumer"
    INDUSTRIAL = "Industrial"
    UTILITIES = "Utilities"
    REAL_ESTATE = "Real Estate"
    UNKNOWN = "Unknown"


class RiskLevel(str, Enum):
    """Risk level classification for assets."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class Ticker:
    """Represents a stock ticker with sector and risk classification."""
    symbol: str
    sector: Sector
    risk_level: RiskLevel

    def __str__(self) -> str:
        return f"{self.symbol} ({self.sector.value}, {self.risk_level.value})"
