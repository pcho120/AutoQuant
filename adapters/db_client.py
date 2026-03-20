from typing import List, Optional
from supabase import create_client
from domain.position import Position, Order
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class DBClient:
    """Adapter for Supabase database operations on positions and orders."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")

        self.supabase = create_client(supabase_url, supabase_key)

    def fetch_positions(self, user_id: str) -> List[Position]:
        """
        Fetch all positions for a user from the database.

        Args:
            user_id: User identifier

        Returns:
            List of Position objects
        """
        try:
            response = self.supabase.table("holdings").select("*").eq("user_id", user_id).execute()
            positions = []
            for row in response.data:
                position = Position(
                    ticker=row["ticker"],
                    quantity=float(row["quantity"]),
                    buy_price=float(row["buy_price"]),
                    current_price=float(row.get("current_price", 0.0))
                )
                positions.append(position)
            return positions
        except Exception:
            return []

    def save_positions(self, user_id: str, positions: List[Position]) -> None:
        """
        Save positions for a user (delete all existing, then insert new ones).

        Args:
            user_id: User identifier
            positions: List of Position objects to save
        """
        try:
            # Delete all existing positions for this user
            self.supabase.table("holdings").delete().eq("user_id", user_id).execute()

            # Insert new positions
            for position in positions:
                self.supabase.table("holdings").insert({
                    "user_id": user_id,
                    "ticker": position.ticker,
                    "quantity": position.quantity,
                    "buy_price": position.buy_price
                }).execute()
        except Exception:
            pass

    def fetch_orders(self, user_id: str) -> List[Order]:
        """
        Fetch all orders for a user from the database.

        Args:
            user_id: User identifier

        Returns:
            List of Order objects
        """
        try:
            response = self.supabase.table("orders").select("*").eq("user_id", user_id).execute()
            orders = []
            for row in response.data:
                # Parse timestamp if it's a string (ISO format from DB)
                timestamp = row["timestamp"]
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                order = Order(
                    ticker=row["ticker"],
                    action=row["action"],
                    quantity=float(row["quantity"]),
                    price=float(row["price"]),
                    timestamp=timestamp,
                    fee=float(row.get("fee", 0.0))
                )
                orders.append(order)
            return orders
        except Exception:
            return []

    def save_order(self, user_id: str, order: Order) -> bool:
        """
        Save a single order to the database.

        Args:
            user_id: User identifier
            order: Order object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table("orders").insert({
                "user_id": user_id,
                "ticker": order.ticker,
                "action": order.action,
                "quantity": order.quantity,
                "price": order.price,
                "timestamp": order.timestamp.isoformat(),
                "fee": order.fee
            }).execute()
            return True
        except Exception:
            return False

    def update_position(self, user_id: str, ticker: str, quantity: float, buy_price: float) -> bool:
        """
        Update a single position in the database.

        Args:
            user_id: User identifier
            ticker: Stock ticker symbol
            quantity: Updated quantity
            buy_price: Updated buy price

        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table("holdings").update({
                "quantity": quantity,
                "buy_price": buy_price
            }).eq("user_id", user_id).eq("ticker", ticker).execute()
            return True
        except Exception:
            return False

    def delete_position(self, user_id: str, ticker: str) -> bool:
        """
        Delete a single position from the database.

        Args:
            user_id: User identifier
            ticker: Stock ticker symbol

        Returns:
            True if successful, False otherwise
        """
        try:
            self.supabase.table("holdings").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
            return True
        except Exception:
            return False
