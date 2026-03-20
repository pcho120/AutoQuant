from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Represents a single position in a portfolio."""
    ticker: str
    quantity: float
    buy_price: float
    current_price: float

    @property
    def market_value(self) -> float:
        """Total current value of the position."""
        return self.quantity * self.current_price

    @property
    def pnl_dollars(self) -> float:
        """Profit/loss in dollars."""
        if self.buy_price == 0:
            return 0.0
        return self.quantity * (self.current_price - self.buy_price)

    @property
    def pnl_percent(self) -> float:
        """Profit/loss in percentage."""
        if self.buy_price == 0:
            return 0.0
        return ((self.current_price - self.buy_price) / self.buy_price) * 100


@dataclass
class Portfolio:
    """Represents a portfolio of positions."""
    positions: list
    cash: float

    @property
    def total_value(self) -> float:
        """Total portfolio value (positions + cash)."""
        positions_value = sum(p.market_value for p in self.positions)
        return positions_value + self.cash

    @property
    def invested_value(self) -> float:
        """Total value invested in positions."""
        return sum(p.market_value for p in self.positions)

    def to_dataframe(self):
        """Convert portfolio to pandas DataFrame."""
        import pandas as pd

        data = []
        for position in self.positions:
            data.append({
                "Ticker": position.ticker,
                "Quantity": position.quantity,
                "Buy Price": position.buy_price,
                "Current Price": position.current_price,
                "Mkt Value": position.market_value,
                "P/L ($)": position.pnl_dollars,
                "P/L (%)": position.pnl_percent,
            })
        return pd.DataFrame(data)


@dataclass
class Order:
    """Represents a trading order."""
    ticker: str
    action: str
    quantity: float
    price: float
    timestamp: datetime
    fee: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost of the order including fee."""
        return (self.quantity * self.price) + self.fee
