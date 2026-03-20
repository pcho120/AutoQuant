import streamlit as st
import datetime
import pandas as pd
from domain.position import Order, Position
from components.ticker_search import render_ticker_search
from adapters import DBClient, MarketDataAdapter


@st.cache_resource
def get_db_client():
    """Get cached database client instance."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return DBClient()


@st.cache_resource
def get_market_data():
    """Get cached market data adapter instance."""
    return MarketDataAdapter()


def render_trading_tab(trading_service):
    """
    Render the paper trading tab.

    Args:
        trading_service: The initialized TradingService instance.
    """
    st.header("Paper Trading")

    # Initialize session cash safely when absent
    if 'cash' not in st.session_state:
        st.session_state.cash = 100000.0  # Default starting cash

    st.subheader(f"Current Balance: ${st.session_state.cash:,.2f}")

    user_id = "user123"
    db_client = get_db_client()
    market_data = get_market_data()

    try:
        with st.spinner("Loading holdings..."):
            positions = db_client.fetch_positions(user_id)

        if positions:
            tickers = [p.ticker for p in positions]
            prices = market_data.fetch_current_prices(tickers)

            holdings_data = []
            for position in positions:
                current_price = prices.get(position.ticker, 0.0)
                unrealized_pl = (current_price - position.buy_price) * position.quantity
                holdings_data.append({
                    "Ticker": position.ticker,
                    "Quantity": position.quantity,
                    "Buy Price": position.buy_price,
                    "Current Price": current_price,
                    "Unrealized P/L": unrealized_pl
                })

            holdings_df = pd.DataFrame(holdings_data)
            st.subheader("Holdings")
            edited_holdings_df = st.data_editor(
                holdings_df,
                num_rows="dynamic",
                use_container_width=True,
                on_change=None,
                key="paper_trading_holdings_editor",
                disabled=["Ticker", "Current Price", "Unrealized P/L"]
            )

            if st.button("💾 Save Holdings"):
                editor_state = st.session_state.get("paper_trading_holdings_editor", {})
                edited_rows = editor_state.get("edited_rows", {})
                deleted_rows = editor_state.get("deleted_rows", [])
                added_rows = editor_state.get("added_rows", [])

                has_errors = False

                for row_idx, changes in edited_rows.items():
                    row_idx = int(row_idx)
                    if row_idx < len(edited_holdings_df):
                        row_data = edited_holdings_df.iloc[row_idx]
                        qty = changes.get("Quantity", row_data.get("Quantity", 0))
                        price = changes.get("Buy Price", row_data.get("Buy Price", 0))

                        if qty <= 0:
                            st.error(f"Row {row_idx + 1}: Quantity must be greater than 0")
                            has_errors = True
                        if price < 0:
                            st.error(f"Row {row_idx + 1}: Buy Price cannot be negative")
                            has_errors = True

                for row_idx in added_rows:
                    if isinstance(row_idx, int) and row_idx < len(edited_holdings_df):
                        row_data = edited_holdings_df.iloc[row_idx]
                        ticker = row_data.get("Ticker", "")
                        qty = row_data.get("Quantity", 0)
                        price = row_data.get("Buy Price", 0)

                        if not ticker:
                            st.error("Added row: Ticker is required")
                            has_errors = True
                        if qty <= 0:
                            st.error("Added row: Quantity must be greater than 0")
                            has_errors = True
                        if price < 0:
                            st.error("Added row: Buy Price cannot be negative")
                            has_errors = True

                if has_errors:
                    st.stop()

                save_success = True

                try:
                    for row_idx in deleted_rows:
                        row_idx = int(row_idx)
                        if row_idx < len(holdings_df):
                            ticker = str(holdings_df.iloc[row_idx]["Ticker"])
                            if not db_client.delete_position(user_id, ticker):
                                st.error(f"Failed to delete {ticker}")
                                save_success = False
                except Exception:
                    st.error("Unable to delete holdings. Please try again.")
                    save_success = False

                try:
                    for row_idx, changes in edited_rows.items():
                        row_idx = int(row_idx)
                        if row_idx < len(holdings_df):
                            ticker = str(holdings_df.iloc[row_idx]["Ticker"])
                            new_qty = float(changes.get("Quantity", holdings_df.iloc[row_idx]["Quantity"]))
                            new_price = float(changes.get("Buy Price", holdings_df.iloc[row_idx]["Buy Price"]))
                            if not db_client.update_position(user_id, ticker, new_qty, new_price):
                                st.error(f"Failed to update {ticker}")
                                save_success = False
                except Exception:
                    st.error("Unable to update holdings. Please try again.")
                    save_success = False

                if added_rows:
                    try:
                        new_positions = []
                        added_tickers = set()
                        for row_idx in added_rows:
                            try:
                                idx = int(row_idx)
                            except (ValueError, TypeError):
                                continue
                            if idx < len(edited_holdings_df):
                                row_data = edited_holdings_df.iloc[idx]
                                ticker = str(row_data.get("Ticker", "")).strip()
                                qty = float(row_data.get("Quantity", 0))
                                price = float(row_data.get("Buy Price", 0))
                                if ticker and qty > 0 and price >= 0:
                                    new_positions.append(Position(ticker=ticker, quantity=qty, buy_price=price, current_price=0.0))
                                    added_tickers.add(ticker)

                        if new_positions:
                            existing_positions = db_client.fetch_positions(user_id)
                            edited_tickers = set(edited_holdings_df["Ticker"])
                            existing_to_keep = [p for p in existing_positions if p.ticker in edited_tickers and p.ticker not in added_tickers]
                            all_positions = existing_to_keep + new_positions
                            db_client.save_positions(user_id, all_positions)

                            persisted_positions = db_client.fetch_positions(user_id)
                            persisted_tickers = set(p.ticker for p in persisted_positions)
                            for added_ticker in added_tickers:
                                if added_ticker not in persisted_tickers:
                                    st.error(f"Failed to verify new position {added_ticker}")
                                    save_success = False
                    except Exception:
                        st.error("Unable to save new holdings. Please try again.")
                        save_success = False

                if save_success:
                    st.success("Holdings saved successfully!")
                    st.rerun()
        else:
            st.info("No holdings yet. Search for a ticker below to start trading.")
    except Exception:
        st.error("Unable to connect to database. Please try again later.")

    st.divider()

    # Input fields
    ticker = render_ticker_search(key="paper_trading_ticker", placeholder="Search ticker...").upper()
    action = st.radio("Action", ["BUY", "SELL"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    with col2:
        price = st.number_input("Price ($)", min_value=0.01, value=100.0, step=0.01, format="%.2f")

    # Execute button
    submitted = st.button("Execute Order")

    if submitted:
        if not ticker:
            st.error("Please enter a valid Ticker.")
        else:
            # Create an Order instance
            order = Order(
                ticker=ticker,
                action=action,
                quantity=quantity,
                price=price,
                timestamp=datetime.datetime.now()
            )

            # We assume a fixed user_id 'user123' for paper trading right now
            user_id = "user123"

            # Execute order via service
            result = trading_service.execute_order(
                user_id=user_id,
                order=order,
                cash_balance=st.session_state.cash
            )

            # Show success/failure message from service response
            if result.get("status") == "SUCCESS":
                st.success(f"Order executed successfully! ({action} {quantity} {ticker})")
                if "fee" in result:
                    st.info(f"Transaction Fee: ${result['fee']:.2f}")
                # Update session cash
                st.session_state.cash = result["remaining_cash"]
                st.rerun()
            else:
                reason = result.get("reason", "Unknown error")
                st.error(f"Order failed: {reason}")
