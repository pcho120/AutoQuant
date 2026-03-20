import pandas as pd
import plotly.graph_objects as pt
import streamlit as st
import ta
import yfinance as yf
from datetime import datetime
from plotly.subplots import make_subplots
from streamlit_searchbox import st_searchbox
from supabase import create_client


class PaperTradingManager:
    def __init__(self):
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        self.supabase = create_client(url, key)
        
        # Trading parameters
        self.INITIAL_CASH = 100000.0
        self.TRANSACTION_FEE_RATE = 0.001  # 0.1% per trade (realistic broker fee)
        
        # Initialize session states
        if "paper_cash" not in st.session_state:
            st.session_state.paper_cash = self.INITIAL_CASH
        if "selected_ticker" not in st.session_state:
            st.session_state.selected_ticker = None
        if "paper_saving" not in st.session_state:
            st.session_state.paper_saving = False
        
        # Load paper portfolio from database
        self.df = self.fetch_paper_portfolio_from_db()
    
    def fetch_paper_portfolio_from_db(self):
        """Fetch paper trading portfolio from database"""
        try:
            response = self.supabase.table("Paper_Portfolio").select("*").execute()
            df = pd.DataFrame(response.data)
            
            if df.empty:
                return pd.DataFrame(columns=["id", "Ticker", "Quantity", "Avg Price", "Total Cost", "Current Price", "Mkt Value", "P/L ($)", "P/L (%)"])
            
            return df
        
        except Exception as e:
            # If table doesn't exist or error, return empty DataFrame
            st.warning(f"Paper trading portfolio not found. Will create on first trade. ({e})")
            return pd.DataFrame(columns=["id", "Ticker", "Quantity", "Avg Price", "Total Cost", "Current Price", "Mkt Value", "P/L ($)", "P/L (%)"])
    
    def get_current_price(self, ticker: str) -> float:
        """Get current price for a single ticker"""
        try:
            data = yf.Ticker(ticker).history(period="1d")
            if not data.empty:
                return round(data["Close"].iloc[-1], 2)
            return None
        except Exception:
            return None
    
    def calculate_transaction_fee(self, amount: float) -> float:
        """Calculate realistic transaction fee"""
        return round(amount * self.TRANSACTION_FEE_RATE, 2)
    
    def execute_buy(self, ticker: str, quantity: int, price: float):
        """Execute a buy order"""
        try:
            # Calculate costs
            cost = quantity * price
            fee = self.calculate_transaction_fee(cost)
            total_cost = cost + fee
            
            # Check if enough cash
            if st.session_state.paper_cash < total_cost:
                st.error(f"Insufficient funds! Need ${total_cost:,.2f}, have ${st.session_state.paper_cash:,.2f}")
                return False
            
            # Deduct cash
            st.session_state.paper_cash -= total_cost
            
            # Check if ticker exists in portfolio
            response = self.supabase.table("Paper_Portfolio").select("*").eq("Ticker", ticker).execute()
            
            if response.data:
                # Update existing position
                existing = response.data[0]
                old_qty = int(existing.get("Quantity", 0))
                old_avg_price = float(existing.get("Avg Price", 0))
                old_total_cost = float(existing.get("Total Cost", 0))
                
                new_qty = old_qty + quantity
                new_total_cost = old_total_cost + total_cost
                new_avg_price = new_total_cost / new_qty
                
                self.supabase.table("Paper_Portfolio").update({
                    "Quantity": new_qty,
                    "Avg Price": round(new_avg_price, 2),
                    "Total Cost": round(new_total_cost, 2)
                }).eq("id", existing["id"]).execute()
            else:
                # Create new position
                self.supabase.table("Paper_Portfolio").insert({
                    "Ticker": ticker,
                    "Quantity": quantity,
                    "Avg Price": round(price, 2),
                    "Total Cost": round(total_cost, 2)
                }).execute()
            
            st.success(f"✅ Bought {quantity} shares of {ticker} @ ${price:.2f} (Fee: ${fee:.2f})")
            return True
        
        except Exception as e:
            st.error(f"Error executing buy order: {e}")
            return False
    
    def execute_sell(self, ticker: str, quantity: int, price: float):
        """Execute a sell order"""
        try:
            # Check if position exists
            response = self.supabase.table("Paper_Portfolio").select("*").eq("Ticker", ticker).execute()
            
            if not response.data:
                st.error(f"You don't own {ticker}")
                return False
            
            existing = response.data[0]
            owned_qty = int(existing.get("Quantity", 0))
            
            if owned_qty < quantity:
                st.error(f"Insufficient shares! You own {owned_qty}, trying to sell {quantity}")
                return False
            
            # Calculate proceeds
            proceeds = quantity * price
            fee = self.calculate_transaction_fee(proceeds)
            net_proceeds = proceeds - fee
            
            # Add cash
            st.session_state.paper_cash += net_proceeds
            
            # Update position
            new_qty = owned_qty - quantity
            
            if new_qty == 0:
                # Close position
                self.supabase.table("Paper_Portfolio").delete().eq("id", existing["id"]).execute()
            else:
                # Reduce position
                old_total_cost = float(existing.get("Total Cost", 0))
                cost_per_share = old_total_cost / owned_qty
                new_total_cost = new_qty * cost_per_share
                
                self.supabase.table("Paper_Portfolio").update({
                    "Quantity": new_qty,
                    "Total Cost": round(new_total_cost, 2)
                }).eq("id", existing["id"]).execute()
            
            st.success(f"✅ Sold {quantity} shares of {ticker} @ ${price:.2f} (Fee: ${fee:.2f})")
            return True
        
        except Exception as e:
            st.error(f"Error executing sell order: {e}")
            return False
    
    def render_paper_portfolio_table(self):
        """Render paper trading portfolio table"""
        st.subheader("Paper Trading Portfolio")
        
        df = self.df.copy()
        
        if df.empty or len(df) == 0:
            st.info("No paper positions yet. Search for a ticker below to start trading!")
            return df
        
        # Get current prices
        tickers = df["Ticker"].dropna().unique().tolist()
        for ticker in tickers:
            current_price = self.get_current_price(ticker)
            df.loc[df["Ticker"] == ticker, "Current Price"] = current_price
        
        # Calculate metrics
        df["Mkt Value"] = df["Quantity"] * df["Current Price"]
        df["P/L ($)"] = df["Mkt Value"] - df["Total Cost"]
        df["P/L (%)"] = ((df["Mkt Value"] - df["Total Cost"]) / df["Total Cost"] * 100).round(2)
        
        # Sort by ID
        if "id" in df.columns:
            df = df.sort_values(by="id")
        
        # Display table
        display_df = df[["id", "Ticker", "Quantity", "Avg Price", "Current Price", "Mkt Value", "P/L ($)", "P/L (%)"]]
        st.dataframe(display_df, use_container_width=True)
        
        # Portfolio summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💵 Cash", f"${st.session_state.paper_cash:,.2f}")
        with col2:
            total_value = df["Mkt Value"].sum() if not df.empty else 0
            st.metric("📈 Portfolio Value", f"${total_value:,.2f}")
        with col3:
            total_account = st.session_state.paper_cash + total_value
            st.metric("💰 Total Account", f"${total_account:,.2f}")
        with col4:
            total_pl = total_account - self.INITIAL_CASH
            pl_pct = (total_pl / self.INITIAL_CASH * 100) if self.INITIAL_CASH > 0 else 0
            st.metric("📊 Total P/L", f"${total_pl:,.2f} ({pl_pct:.2f}%)")
        
        return df
    
    def search_ticker(self, searchterm: str) -> list:
        """
        Search for ticker symbols and return results with company names.
        Returns list of tuples: (display_text, ticker_symbol)
        """
        if not searchterm or len(searchterm) < 1:
            # Return popular tickers as default options
            default_tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "AMD", "NFLX", "DIS"]
            results = []
            for ticker in default_tickers:
                try:
                    t = yf.Ticker(ticker)
                    info = t.info
                    company_name = info.get("longName") or info.get("shortName") or ticker
                    results.append((f"{ticker} - {company_name}", ticker))
                except:
                    results.append((ticker, ticker))
            return results
        
        # Search logic: Try ticker first, then search by company name
        searchterm_upper = searchterm.upper().strip()
        results = []
        
        # Direct ticker lookup
        try:
            t = yf.Ticker(searchterm_upper)
            info = t.info
            
            # Check if it's a valid ticker (has a symbol)
            if info.get("symbol"):
                company_name = info.get("longName") or info.get("shortName") or searchterm_upper
                results.append((f"{searchterm_upper} - {company_name}", searchterm_upper))
        except:
            pass
        
        # Try common variations (for Google -> GOOGL, etc.)
        ticker_mappings = {
            "GOOGLE": ["GOOGL", "GOOG"],
            "FACEBOOK": ["META"],
            "TESLA": ["TSLA"],
            "APPLE": ["AAPL"],
            "MICROSOFT": ["MSFT"],
            "AMAZON": ["AMZN"],
            "NVIDIA": ["NVDA"],
            "NETFLIX": ["NFLX"],
            "DISNEY": ["DIS"],
            "AMD": ["AMD"],
        }
        
        # Check if search term matches a company name
        for company, tickers in ticker_mappings.items():
            if company in searchterm_upper or searchterm_upper in company:
                for ticker in tickers:
                    try:
                        t = yf.Ticker(ticker)
                        info = t.info
                        if info.get("symbol"):
                            company_name = info.get("longName") or info.get("shortName") or ticker
                            # Avoid duplicates
                            if not any(r[1] == ticker for r in results):
                                results.append((f"{ticker} - {company_name}", ticker))
                    except:
                        pass
        
        # If no results yet, try partial ticker match on popular stocks
        if not results:
            popular_tickers = ["AAPL", "GOOGL", "GOOG", "MSFT", "TSLA", "NVDA", "AMZN", "META", "AMD", "NFLX", "DIS", "BABA", "TSM", "V", "JPM", "WMT", "MA", "UNH", "JNJ", "HD"]
            for ticker in popular_tickers:
                if searchterm_upper in ticker:
                    try:
                        t = yf.Ticker(ticker)
                        info = t.info
                        if info.get("symbol"):
                            company_name = info.get("longName") or info.get("shortName") or ticker
                            results.append((f"{ticker} - {company_name}", ticker))
                    except:
                        pass
        
        return results[:10]  # Limit to 10 results
    
    def render_ticker_search(self):
        """Render ticker search using streamlit-searchbox with autocomplete"""
        st.subheader("Search Ticker")
        
        # Use streamlit-searchbox for autocomplete
        selected = st_searchbox(
            self.search_ticker,
            placeholder="Search ticker or company name (e.g., AAPL, Apple, Google)...",
            label=None,
            key="ticker_searchbox",
            clear_on_submit=False,
            default=None
        )
        
        if selected:
            # selected is the ticker symbol
            st.session_state.selected_ticker = selected
            current_price = self.get_current_price(selected)
            if current_price:
                st.success(f"✅ Selected {selected} - Current Price: ${current_price:.2f}")
            else:
                st.error(f"❌ Could not fetch price for {selected}")
    
    def render_trading_interface(self):
        """Render buy/sell interface and enhanced chart"""
        if not st.session_state.selected_ticker:
            st.info("👆 Search for a ticker above to start trading")
            return
        
        ticker = st.session_state.selected_ticker
        current_price = self.get_current_price(ticker)
        
        if not current_price:
            st.error(f"Could not fetch price for {ticker}")
            return
        
        # Layout: Left (Trading Interface) + Right (Chart)
        col_left, col_right = st.columns([1, 3])
        
        with col_left:
            st.subheader(f"{ticker}")
            st.metric("Current Price", f"${current_price:.2f}")
            
            # Buy/Sell tabs
            trade_tab1, trade_tab2 = st.tabs(["🟢 Buy", "🔴 Sell"])
            
            with trade_tab1:
                st.write("**Buy Order**")
                buy_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key="buy_qty")
                buy_cost = buy_qty * current_price
                buy_fee = self.calculate_transaction_fee(buy_cost)
                buy_total = buy_cost + buy_fee
                
                st.write(f"Cost: ${buy_cost:,.2f}")
                st.write(f"Fee: ${buy_fee:.2f}")
                st.write(f"**Total: ${buy_total:,.2f}**")
                
                if st.button("Buy", key="execute_buy", type="primary"):
                    if self.execute_buy(ticker, buy_qty, current_price):
                        self.df = self.fetch_paper_portfolio_from_db()
                        st.rerun()
            
            with trade_tab2:
                st.write("**Sell Order**")
                
                # Check owned quantity
                response = self.supabase.table("Paper_Portfolio").select("*").eq("Ticker", ticker).execute()
                owned_qty = 0
                if response.data:
                    owned_qty = int(response.data[0].get("Quantity", 0))
                
                st.write(f"You own: **{owned_qty}** shares")
                
                if owned_qty > 0:
                    sell_qty = st.number_input("Quantity", min_value=1, max_value=owned_qty, value=min(1, owned_qty), step=1, key="sell_qty")
                    sell_proceeds = sell_qty * current_price
                    sell_fee = self.calculate_transaction_fee(sell_proceeds)
                    sell_net = sell_proceeds - sell_fee
                    
                    st.write(f"Proceeds: ${sell_proceeds:,.2f}")
                    st.write(f"Fee: ${sell_fee:.2f}")
                    st.write(f"**Net: ${sell_net:,.2f}**")
                    
                    if st.button("Sell", key="execute_sell", type="primary"):
                        if self.execute_sell(ticker, sell_qty, current_price):
                            self.df = self.fetch_paper_portfolio_from_db()
                            st.rerun()
                else:
                    st.info("You don't own this stock")
        
        with col_right:
            self.render_enhanced_chart(ticker)
    
    def render_enhanced_chart(self, ticker: str):
        """Render enhanced chart with multiple technical indicators"""
        st.subheader(f"{ticker} Chart")
        
        # Period, interval, and height selectors
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            period = st.selectbox("Period", ["5d", "1mo", "3mo", "6mo", "1y"], index=1, key="paper_period")
        with col2:
            interval = st.selectbox("Interval", ["15m", "1h", "1d"], index=1, key="paper_interval")
        with col3:
            chart_height = st.slider("Chart Height", min_value=600, max_value=1500, value=1000, step=50, key="paper_chart_height")
        
        try:
            # Download price data
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            if data.empty:
                st.warning("No data available for this selection")
                return
            
            # Handle MultiIndex columns
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Calculate technical indicators
            # RSI (14)
            rsi_raw = ta.momentum.RSIIndicator(close=data["Close"], window=14).rsi()
            data["RSI"] = rsi_raw.ewm(span=6, adjust=False).mean().round(2)
            
            # MACD
            macd = ta.trend.MACD(close=data["Close"])
            data["MACD"] = macd.macd()
            data["MACD_signal"] = macd.macd_signal()
            data["MACD_hist"] = macd.macd_diff()
            
            # KDJ (Stochastic)
            stoch = ta.momentum.StochasticOscillator(high=data["High"], low=data["Low"], close=data["Close"], window=14, smooth_window=3)
            data["K"] = stoch.stoch()
            data["D"] = stoch.stoch_signal()
            data["J"] = 3 * data["K"] - 2 * data["D"]
            
            # CCI (Commodity Channel Index)
            cci = ta.trend.CCIIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=20)
            data["CCI"] = cci.cci()
            
            data.dropna(inplace=True)
            
            # Create 5-row subplot (Candlestick + 4 indicators)
            fig = make_subplots(
                rows=5,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.02,
                row_heights=[0.4, 0.15, 0.15, 0.15, 0.15],
                subplot_titles=(f"{ticker} Candlestick", "RSI (14)", "MACD", "KDJ", "CCI")
            )
            
            # Row 1: Candlestick
            fig.add_trace(
                pt.Candlestick(
                    x=data.index,
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    name="Price",
                    text=[
                        f"Open: {o:.2f}<br>High: {h:.2f}<br>Low: {l:.2f}<br>Close: {c:.2f}"
                        for o, h, l, c in zip(data["Open"], data["High"], data["Low"], data["Close"])
                    ],
                    hoverinfo="text",
                    hoverlabel=dict(namelength=0)
                ),
                row=1, col=1
            )
            
            # Row 2: RSI
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["RSI"], mode="lines", name="RSI", line=dict(color="cyan", width=2)),
                row=2, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.4, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.4, row=2, col=1)
            
            # Row 3: MACD
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["MACD"], mode="lines", name="MACD", line=dict(color="blue", width=2)),
                row=3, col=1
            )
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["MACD_signal"], mode="lines", name="Signal", line=dict(color="orange", width=2)),
                row=3, col=1
            )
            fig.add_trace(
                pt.Bar(x=data.index, y=data["MACD_hist"], name="Histogram", marker_color="gray"),
                row=3, col=1
            )
            
            # Row 4: KDJ
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["K"], mode="lines", name="K", line=dict(color="blue", width=2)),
                row=4, col=1
            )
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["D"], mode="lines", name="D", line=dict(color="red", width=2)),
                row=4, col=1
            )
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["J"], mode="lines", name="J", line=dict(color="green", width=2)),
                row=4, col=1
            )
            fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.3, row=4, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.3, row=4, col=1)
            
            # Row 5: CCI
            fig.add_trace(
                pt.Scatter(x=data.index, y=data["CCI"], mode="lines", name="CCI", line=dict(color="purple", width=2)),
                row=5, col=1
            )
            fig.add_hline(y=100, line_dash="dash", line_color="red", opacity=0.4, row=5, col=1)
            fig.add_hline(y=-100, line_dash="dash", line_color="green", opacity=0.4, row=5, col=1)
            
            # Layout polish
            fig.update_layout(
                height=chart_height,
                hovermode="x unified",
                xaxis_rangeslider_visible=False,
                showlegend=False,
                margin=dict(t=40, b=40)
            )
            
            # Y-axis formatting (all on right side)
            fig.update_yaxes(side="right", showgrid=True, row=1, col=1)
            fig.update_yaxes(side="right", showgrid=True, range=[0, 100], row=2, col=1)
            fig.update_yaxes(side="right", showgrid=True, row=3, col=1)
            fig.update_yaxes(side="right", showgrid=True, range=[0, 100], row=4, col=1)
            fig.update_yaxes(side="right", showgrid=True, row=5, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error loading chart: {e}")
    
    def render_paper_trading(self):
        """Main render method for paper trading tab"""
        st.header("Paper Trading")
        
        # 1. Paper portfolio table
        self.render_paper_portfolio_table()
        
        st.divider()
        
        # 2. Ticker search
        self.render_ticker_search()
        
        st.divider()
        
        # 3. Trading interface + Chart
        self.render_trading_interface()
