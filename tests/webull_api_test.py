import os
from dotenv import load_dotenv
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

load_dotenv()

APP_KEY = os.getenv("WEBULL_APP_KEY")
APP_SECRET = os.getenv("WEBULL_APP_SECRET")
REGION = os.getenv("WEBULL_REGION", "us")

def get_webull_portfolio():
    api_client = ApiClient(APP_KEY, APP_SECRET, REGION)
    trade_client = TradeClient(api_client)

    # Fetch account list
    accounts_res = trade_client.account_v2.get_account_list()
    
    # Check response payload structure
    res_data = accounts_res.json() if hasattr(accounts_res, 'json') else accounts_res

    if isinstance(res_data, list):
        accounts = res_data
    elif isinstance(res_data, dict):
        accounts = res_data.get("accounts", [])
    else:
        accounts = []

    print(f"\n=== Total Linked Accounts: {len(accounts)} ===")

    portfolio_summary = []

    for acc in accounts:
        # Handle dict response
        acc_id = acc.get("account_id") or acc.get("accountId")
        acc_type = acc.get("account_type") or acc.get("accountType", "UNKNOWN")
        net_value = acc.get("net_liquidation") or acc.get("netLiquidation", 0)

        print(f"\n📂 Account Type: {acc_type} (ID: {acc_id}) | Net Liquidation: ${net_value}")
        print("-" * 65)

        # Fetch positions for each account
        pos_res = trade_client.account_v2.get_account_position(account_id=acc_id)
        pos_data = pos_res.json() if hasattr(pos_res, 'json') else pos_res

        if isinstance(pos_data, list):
            positions = pos_data
        elif isinstance(pos_data, dict):
            positions = pos_data.get("positions", [])
        else:
            positions = []

        if not positions:
            print("   (No open positions)")

        for p in positions:
            info = {
                "account_type": acc_type,
                "ticker": p.get("symbol") or p.get("ticker"),
                "quantity": p.get("quantity") or p.get("position"),
                "avg_cost": p.get("cost_price") or p.get("costPrice"),
                "market_val": p.get("market_value") or p.get("marketValue"),
                "pnl": p.get("unrealized_pnl") or p.get("unrealizedPnl")
            }
            portfolio_summary.append(info)

            print(f"   • {info['ticker']:<6} | Qty: {info['quantity']:<4} | Avg Cost: ${float(info['avg_cost'] or 0):<7.2f} | Mkt Val: ${float(info['market_val'] or 0):<8.2f}")

    return portfolio_summary

if __name__ == "__main__":
    get_webull_portfolio()