from typing import List
from domain.position import Position


class TradingService:
    """Service for executing trading orders and calculating portfolio PnL.
    
    Uses the 'paper_portfolio' table for all position read/write operations during paper trading simulation.
    """

    FEE_RATE = 0.001  # 0.1% transaction fee
    SLIPPAGE_RATE = 0.0005  # 0.05% simulated market-order slippage

    def __init__(self, db, market):
        """
        Initialize the trading service.

        Args:
            db: Database adapter (DBClient)
            market: Market data adapter (MarketDataAdapter)
        """
        self.db = db
        self.market = market

    def execute_order(
        self,
        user_id: str,
        ticker: str,
        action: str,
        quantity: float,
        order_type: str,
        limit_price: float | None = None,
    ) -> dict:
        quote = self.market.fetch_trade_quote(ticker)
        regular_session = quote["regularSession"]
        closed_session_buy = action == "BUY" and quote["afterHoursBuyAllowed"]
        if action == "SELL" and not quote["marketOpen"]:
            return {"status": "FAILED", "reason": "Sell orders require an open regular market"}
        if action == "BUY" and regular_session and not quote["marketOpen"]:
            return {"status": "FAILED", "reason": "The live market quote is stale"}
        if action == "BUY" and not regular_session and not closed_session_buy:
            return {"status": "FAILED", "reason": "No recent closing price is available"}

        quote_price = quote["price"]
        if order_type == "LIMIT":
            if limit_price is None:
                return {"status": "FAILED", "reason": "Limit price is required"}
            can_fill = quote_price <= limit_price if action == "BUY" else quote_price >= limit_price
            if not can_fill:
                return {"status": "FAILED", "reason": "Limit price has not been reached"}
            filled_price = quote_price
        else:
            if closed_session_buy:
                filled_price = quote_price
            else:
                direction = 1 if action == "BUY" else -1
                filled_price = quote_price * (1 + direction * self.SLIPPAGE_RATE)

        filled_quantity = min(quantity, quote.get("availableQuantity", quantity))
        if filled_quantity <= 0:
            return {"status": "FAILED", "reason": "No executable market liquidity is available"}

        execution_session = "CLOSED" if closed_session_buy else "REGULAR"
        try:
            result = self.db.execute_paper_order(
                user_id=user_id,
                ticker=ticker,
                action=action,
                order_type=order_type,
                requested_quantity=quantity,
                filled_quantity=filled_quantity,
                requested_price=limit_price,
                filled_price=filled_price,
                fee_rate=self.FEE_RATE,
                quote_timestamp=quote["timestamp"],
                execution_session=execution_session,
            )
        except Exception as exc:
            message = str(exc)
            if "Insufficient cash" in message:
                return {"status": "FAILED", "reason": "Insufficient cash"}
            if "Insufficient quantity" in message:
                return {"status": "FAILED", "reason": "Insufficient quantity"}
            raise
        return {
            **result,
            "quote_price": quote_price,
            "quote_timestamp": quote["timestamp"],
            "execution_session": execution_session,
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
