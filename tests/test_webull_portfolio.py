from unittest.mock import Mock

import pytest

from adapters.webull_portfolio import WebullPortfolioAdapter


def response(data):
    result = Mock()
    result.json.return_value = data
    return result


def test_fetch_portfolio_aggregates_same_ticker_across_accounts():
    adapter = WebullPortfolioAdapter.__new__(WebullPortfolioAdapter)
    adapter.trade_client = Mock()
    adapter.trade_client.account_v2.get_account_list.return_value = response([
        {"account_id": "account-1"},
        {"accountId": "account-2"},
    ])
    adapter.trade_client.account_v2.get_account_position.side_effect = [
        response([{"symbol": "AAPL", "quantity": "2", "cost_price": "100"}]),
        response({"positions": [{"ticker": "aapl", "position": "3", "costPrice": "120"}]}),
    ]

    portfolio = adapter.fetch_portfolio()

    assert portfolio.account_count == 2
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].ticker == "AAPL"
    assert portfolio.positions[0].quantity == 5
    assert portfolio.positions[0].buy_price == 112


def test_fetch_portfolio_rejects_missing_accounts():
    adapter = WebullPortfolioAdapter.__new__(WebullPortfolioAdapter)
    adapter.trade_client = Mock()
    adapter.trade_client.account_v2.get_account_list.return_value = response([])

    with pytest.raises(ValueError, match="No Webull accounts"):
        adapter.fetch_portfolio()