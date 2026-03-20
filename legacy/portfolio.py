import pandas as pd
import plotly.graph_objects as pt
import streamlit as st
import yfinance as yf
from supabase import create_client

#df => from DB. for calculation.
# edited_df => data after 'save' is clicked

class portfolioManager:
    def __init__(self):
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        self.supabase = create_client(url, key)

        #Load portfolio data from database into DataFrame
        self.df = self.fetch_portfolio_from_db()

    #fetch portfolio data from database->DataFrame
    def fetch_portfolio_from_db(self):
        try:
            #Supabase DB->DataFrame
            response = (self.supabase.table("Portfolio").select("*").execute())
            df = pd.DataFrame(response.data)

            #rename DB column names->UI friendly
            rename_map = {
                "Ticker": "Ticker",
                "Quantity": "Quantity",
                "Buy Price": "Buy Price",
                "Sell Price": "Sell Price",
                "Buy Date": "Buy Date",
                "Sell Date": "Sell Date",
                "Status": "Status"
            }
            df.rename(columns=rename_map, inplace=True)

            #st.write("Festched data from supabase:", df)
            #st.write("Columns:", df.columns.tolist())
            return df

        except Exception as e:
            st.error(f"Error fetching portfolio: {e}")
            # Return empty DataFrame with expected columns structure
            return pd.DataFrame(columns=["id", "Ticker", "Quantity", "Buy Price", "Current Price", "Mkt Value", "P/L ($)", "P/L (%)"])

    #toggleable portfolio alloccation pie chart
    def visualize_allocation_button(self, portfolio_df):
        #initialize session_state
        if "show_allocation" not in st.session_state:
            st.session_state.show_allocation = False
        #button toggle
        if st.button("Visualization Portfolio Allocation", key="allocation_toggle"):
            st.session_state.show_allocation = not st.session_state.show_allocation
        #render pie chart only when toggle is on
        if st.session_state.show_allocation:
            #calculate total portfolio value
            total = portfolio_df["Mkt Value"].sum()

            #create calculated columns
            allocation_df = portfolio_df.copy()
            portfolio_df["Allocation"] = (portfolio_df["Mkt Value"] / total * 100).round(2)

            #build pie chart
            fig = pt.Figure(
                data=[
                    pt.Pie(
                        labels=portfolio_df["Ticker"],
                        values=portfolio_df["Mkt Value"],
                        hole=0.3,
                        textinfo="text",    #disable auto % showing by Plotly
                        text=[
                            f"{ticker}"
                            f"<br>{qty} shares"
                            f"<br>${value:,.0f}"
                            f"<br>{alloc:.1f}%"
                            for ticker, alloc, value, qty in zip(
                                portfolio_df["Ticker"],
                                portfolio_df["Allocation"],
                                portfolio_df["Mkt Value"],
                                portfolio_df["Quantity"],
                            )
                        ]
                    )
                ]
            )

            #add total portfolio value in center of the pie chart
            fig.update_layout(
                annotations=[
                    dict(
                        text=f"${portfolio_df['Mkt Value'].sum():,.0f}",
                        x=0.5,
                        y=0.5,
                        font=dict(size=18),
                        showarrow=False,
                    )
                ],
                title="Portfolio Allocation (%)",
                transition = dict(duration=500, easing="cubic-in-out"),
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)

    #Current price from Yahoo Finance API
    def get_current_prices(self, tickers: list[str]) -> dict:
        prices = {}
        for t in tickers:
            try:
                data=yf.Ticker(t).history(period="1d")
                prices[t] = round(data["Close"].iloc[-1], 2)
            except Exception:
                prices[t] = None
        return prices


    """
    Main UI section:
        -editable portfolio table
        -allocation button (left)
        -save button (right)
        -syncs changes back to Supabase DB
    """
    def render_portfolio(self):
        st.subheader("Enter Your Portfolio")
        df = self.df.copy()

        if "editing" not in st.session_state:
            st.session_state.editing = False
        if "show_prices" not in st.session_state:
            st.session_state.show_prices = False

        # Always fetch current prices for existing tickers
        tickers = df["Ticker"].dropna().unique().tolist()
        current_prices = self.get_current_prices(tickers)
        df["Current Price"] = df["Ticker"].map(current_prices)

        # Remove unwanted columns
        columns_to_drop = ["created_at", "Sell Price", "Buy Date", "Sell Date", "Status"]
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])

        # Sort by ID if available
        if "id" in df.columns:
            df = df.sort_values(by="id")

        # Always calculate financial metrics
        df["Mkt Value"] = df["Quantity"] * df["Current Price"]
        df["P/L ($)"] = df["Mkt Value"] - (df["Quantity"] * df["Buy Price"])

        # P/L (%) = portfolio allocation percentage
        total_mkt_value = df["Mkt Value"].sum()
        if total_mkt_value > 0:
            df["P/L (%)"] = (df["Mkt Value"] / total_mkt_value * 100).round(2)
        else:
            df["P/L (%)"] = 0

        #Render editable table (DataFrame->Web table)
        edited_df = st.data_editor(
            df, num_rows="dynamic",
            use_container_width=True,
            disabled=["id", "Mkt Value", "P/L ($)", "P/L (%)"],
            key="portfolio_editor"  #without key, it will not persist state across reruns (table)
        )
        #st.write("DEBUG df columns:", df.columns.tolist())
        #st.write("DEBUG first rows:", df.head(3))
        #st.write("DEBUG editor input columns:", edited_df.columns.tolist())

        col1, col2, col3 = st.columns([6,2,1])
        with col1:
            self.visualize_allocation_button(edited_df)
        with col2:
            # processing indicator (save 버튼 왼쪽)
            if st.session_state.get("saving", False):
                st.spinner("")
        with col3:
            if st.button("Save", key="save_portfolio"):
                st.session_state.editing = False
                st.session_state.show_prices = True
                st.session_state.saving = True

                #clean and enforce data types
                edited_df["Quantity"] = edited_df["Quantity"].fillna(0).astype(int)
                edited_df["Buy Price"] = edited_df["Buy Price"].fillna(0).astype(float)

                #UI->DataFrame->Supabase DB
                for _, row in edited_df.iterrows():
                    #verification. skip invalid rows
                    if pd.isna(row["Ticker"]) or pd.isna(row["Quantity"]) or pd.isna(row["Buy Price"]) or row["Quantity"] == 0 or row["Buy Price"] == 0:
                        continue

                    #normalize input
                    ticker = row["Ticker"].upper().strip()
                    qty = int(row["Quantity"])
                    price = float(row["Buy Price"])

                    #check if Ticker exists in the database
                    response = (self.supabase.table("Portfolio").select("*").eq("Ticker", ticker).execute())

                    if response.data:
                        #exists, update
                        existing = response.data[0]
                        old_qty = int(existing.get("Quantity", 0))
                        old_price = float(existing.get("Buy Price", 0))

                        # Check if this row has an id (it's an existing row being edited)
                        if pd.notna(row.get("id")):
                            # Edit existing row - just update with new values
                            new_qty = qty
                            new_avg_price = price
                            self.supabase.table("Portfolio").update({
                                "Quantity": new_qty,
                                "Buy Price": new_avg_price
                            }).eq("id", existing["id"]).execute()
                        else:
                            # New row added - add to existing quantity and average price
                            new_qty = old_qty + qty
                            if new_qty > 0:
                                new_avg_price = (old_qty * old_price + qty * price) / new_qty

                                self.supabase.table("Portfolio").update({
                                    "Quantity": new_qty,
                                    "Buy Price": new_avg_price
                                }).eq("id", existing["id"]).execute()
                    else:
                        #does not exist, insert
                        self.supabase.table("Portfolio").insert({
                            "Ticker": ticker,
                            "Quantity": qty,
                            "Buy Price": price
                        }).execute()

                #reload data after save
                self.df = self.fetch_portfolio_from_db()

                st.session_state.saving = False
                st.rerun()

        return self.df