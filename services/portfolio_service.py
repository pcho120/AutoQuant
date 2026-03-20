import streamlit as st
from typing import Dict
from domain.ticker import Ticker, Sector, RiskLevel
from domain.position import Portfolio, Position


class PortfolioService:
    """Service for managing portfolio operations including caching and risk labeling.
    
    Uses the 'portfolio' table for all position read/write operations.
    """

    def __init__(self, db, market):
        """
        Initialize the portfolio service.

        Args:
            db: Database adapter (DBClient)
            market: Market data adapter (MarketDataAdapter)
        """
        self.db = db
        self.market = market

    @st.cache_data(ttl=300)
    def get_portfolio(_self, user_id) -> Portfolio:
        """
        Fetch and return a user's portfolio with current prices.

        Caching is applied with TTL of 300 seconds to avoid repeated API calls.

        Args:
            user_id: User identifier

        Returns:
            Portfolio object with positions and current prices
        """
        # Fetch positions from database
        positions = _self.db.fetch_positions(user_id, table_name="portfolio")

        # Get tickers for price lookup
        tickers = [p.ticker for p in positions]

        # Fetch current prices via market adapter
        if tickers:
            prices = _self.market.fetch_current_prices(tickers)
            # Update positions with current prices
            for position in positions:
                position.current_price = prices.get(position.ticker, position.current_price)

        # Return portfolio with cash balance (hardcoded for now, can be extended to fetch from DB)
        return Portfolio(positions=positions, cash=10000.0)

    def update_positions(self, user_id: str, edited_df) -> bool:
        """
        Update positions from an edited DataFrame.

        Converts DataFrame rows back to Position objects and saves to database.

        Args:
            user_id: User identifier
            edited_df: DataFrame with edited position data

        Returns:
            True if successful
        """
        positions = []
        for _, row in edited_df.iterrows():
            position = Position(
                ticker=row["Ticker"],
                quantity=row["Quantity"],
                buy_price=row["Buy Price"],
                current_price=row["Current Price"]
            )
            positions.append(position)

        self.db.save_positions(user_id, positions, table_name="portfolio")
        return True

    def label_risk(self, ticker: Ticker) -> RiskLevel:
        """
        Label risk level for a ticker based on sector.

        Args:
            ticker: Ticker object with sector information

        Returns:
            RiskLevel (HIGH, MEDIUM, or LOW)
        """
        # Tech and Finance are high risk
        if ticker.sector in (Sector.TECH, Sector.FINANCE):
            return RiskLevel.HIGH

        # Utilities, Consumer, Healthcare are medium risk
        if ticker.sector in (Sector.UTILITIES, Sector.CONSUMER, Sector.HEALTHCARE):
            return RiskLevel.MEDIUM

        # Industrial, Energy, Real Estate are medium to high
        if ticker.sector in (Sector.INDUSTRIAL, Sector.ENERGY, Sector.REAL_ESTATE):
            return RiskLevel.MEDIUM

        # Default to medium for unknown
        return RiskLevel.MEDIUM

    def calculate_allocation(self, portfolio: Portfolio) -> Dict[str, float]:
        """
        Calculate portfolio allocation by ticker.

        Args:
            portfolio: Portfolio object

        Returns:
            Dict mapping ticker to allocation percentage
        """
        if portfolio.invested_value == 0:
            return {}

        allocation = {}
        for position in portfolio.positions:
            allocation[position.ticker] = (
                position.market_value / portfolio.total_value
            ) * 100

        return allocation
