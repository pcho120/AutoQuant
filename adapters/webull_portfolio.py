import os
from dataclasses import dataclass

from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

from domain.position import Position


@dataclass(frozen=True)
class WebullPortfolio:
    account_count: int
    positions: list[Position]


class WebullPortfolioAdapter:
    """Read and normalize portfolio positions from Webull OpenAPI."""

    def __init__(self, app_key: str | None = None, app_secret: str | None = None, region: str | None = None):
        app_key = app_key or os.getenv("WEBULL_APP_KEY")
        app_secret = app_secret or os.getenv("WEBULL_APP_SECRET")
        region = region or os.getenv("WEBULL_REGION", "us")
        if not app_key or not app_secret:
            raise ValueError("Webull credentials not found in environment variables")

        api_client = ApiClient(app_key, app_secret, region)
        self.trade_client = TradeClient(api_client)

    @staticmethod
    def _response_data(response):
        return response.json() if hasattr(response, "json") else response

    @staticmethod
    def _items(data, key: str) -> list[dict]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get(key, [])
            return items if isinstance(items, list) else []
        raise ValueError("Unexpected response from Webull")

    def fetch_portfolio(self) -> WebullPortfolio:
        accounts_data = self._response_data(self.trade_client.account_v2.get_account_list())
        accounts = self._items(accounts_data, "accounts")
        if not accounts:
            raise ValueError("No Webull accounts were returned")

        aggregated: dict[str, dict[str, float]] = {}
        for account in accounts:
            account_id = account.get("account_id") or account.get("accountId")
            if not account_id:
                raise ValueError("Webull account response is missing an account ID")

            positions_data = self._response_data(
                self.trade_client.account_v2.get_account_position(account_id=account_id)
            )
            for item in self._items(positions_data, "positions"):
                ticker = str(item.get("symbol") or item.get("ticker") or "").strip().upper()
                quantity = float(item.get("quantity") or item.get("position") or 0)
                average_cost = float(item.get("cost_price") or item.get("costPrice") or 0)
                if not ticker or quantity <= 0 or average_cost < 0:
                    continue

                aggregate = aggregated.setdefault(ticker, {"quantity": 0.0, "cost": 0.0})
                aggregate["quantity"] += quantity
                aggregate["cost"] += quantity * average_cost

        positions = [
            Position(
                ticker=ticker,
                quantity=values["quantity"],
                buy_price=values["cost"] / values["quantity"] if values["quantity"] else 0.0,
                current_price=0.0,
            )
            for ticker, values in sorted(aggregated.items())
        ]
        return WebullPortfolio(account_count=len(accounts), positions=positions)