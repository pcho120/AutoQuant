from typing import Dict, List
from domain.position import Order, Position


class TradingService:
    """Service for executing trading orders and calculating portfolio PnL."""

    FEE_RATE = 0.001  # 0.1% transaction fee

    def __init__(self, db, market):
        """
        Initialize the trading service.

        Args:
            db: Database adapter (DBClient)
            market: Market data adapter (MarketDataAdapter)
        """
        self.db = db
        self.market = market

    def execute_order(self, user_id: str, order: Order, cash_balance: float) -> dict:
        """
        Execute a trading order with validation.

        Args:
            user_id: User identifier
            order: Order object to execute
            cash_balance: Current cash balance

        Returns:
            Dict with keys:
                - status: "SUCCESS" or "FAILED"
                - reason: Failure reason (if FAILED)
                - remaining_cash: Cash after order (if SUCCESS)
                - fee: Transaction fee charged
        """
        # Calculate transaction fee
        fee = order.quantity * order.price * self.FEE_RATE
        order.fee = fee

        if order.action == "BUY":
            total_cost = (order.quantity * order.price) + fee
            
            # Validate sufficient cash
            if total_cost > cash_balance:
                return {
                    "status": "FAILED",
                    "reason": "Insufficient cash"
                }
            
            # Execute buy order
            remaining_cash = cash_balance - total_cost
            self.db.save_order(user_id, order)
            
            return {
                "status": "SUCCESS",
                "remaining_cash": remaining_cash,
                "fee": fee
            }

        elif order.action == "SELL":
            # Fetch current positions to validate quantity
            positions = self.db.fetch_positions(user_id)
            holding = next((p for p in positions if p.ticker == order.ticker), None)
            
            # Validate sufficient quantity
            if holding is None or holding.quantity < order.quantity:
                return {
                    "status": "FAILED",
                    "reason": "Insufficient quantity"
                }
            
            # Execute sell order
            sale_proceeds = (order.quantity * order.price) - fee
            remaining_cash = cash_balance + sale_proceeds
            self.db.save_order(user_id, order)
            
            return {
                "status": "SUCCESS",
                "remaining_cash": remaining_cash,
                "fee": fee
            }

        else:
            return {
                "status": "FAILED",
                "reason": f"Unknown action: {order.action}"
            }

    def calculate_pnl(self, positions: List[Position]) -> dict:
        """
        Calculate total profit/loss for a portfolio.

        Args:
            positions: List of Position objects

        Returns:
            Dict with keys:
                - total_pnl_dollars: Total P/L in dollars
                - total_pnl_percent: Average P/L percentage
                - position_count: Number of positions
        """
        if not positions:
            return {
                "total_pnl_dollars": 0.0,
                "total_pnl_percent": 0.0,
                "position_count": 0
            }

        total_pnl_dollars = sum(p.pnl_dollars for p in positions)
        total_invested = sum(p.quantity * p.buy_price for p in positions)
        
        # Calculate weighted average P/L percentage
        if total_invested > 0:
            total_pnl_percent = (total_pnl_dollars / total_invested) * 100
        else:
            total_pnl_percent = 0.0

        return {
            "total_pnl_dollars": total_pnl_dollars,
            "total_pnl_percent": total_pnl_percent,
            "position_count": len(positions)
        }
