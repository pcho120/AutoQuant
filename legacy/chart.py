import pandas as pd
import plotly.graph_objects as pt
import streamlit as st
import ta
import yfinance as yf
from plotly.subplots import make_subplots


class chartManager:
    def render_chart_section(self, df):
        # Stock selector and controls
        col1, col2, col3, col4 = st.columns([2,1,1,1])
        with col1:
            ticker = st.selectbox("Choose a stock", sorted(df["Ticker"].dropna().unique()))
        with col2:
            period = st.selectbox("Select period", ["5d", "1mo", "3mo", "6mo", "1y"], index=1)
        with col3:
            interval = st.selectbox("Select interval", ["15m", "1h", "1d"], index=1)
        with col4:
            chart_height = st.slider("Chart Height", min_value=400, max_value=1200, value=750, step=50, key="portfolio_chart_height")

        try:
            # Download price data
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            if data.empty:
                st.warning("No data available for this selection")
                return

            # MultiIndex 방어
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # RSI (14)
            rsi_raw = ta.momentum.RSIIndicator(close=data["Close"], window=14).rsi()
            # EMA smoothing
            data["RSI"] = rsi_raw.ewm(span=6, adjust=False).mean()
            data["RSI"] = data["RSI"].round(2)
            data.dropna(inplace=True)

            # Chart layout
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=(f"{ticker} Candlestick","RSI (14)")
            )

            # Candlestick
            fig.add_trace(
                pt.Candlestick(
                    x=data.index,
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    text=[
                            f"Open: {o:.2f}<br>High: {h:.2f}<br>Low: {l:.2f}<br>Close: {c:.2f}"
                            for o, h, l, c in zip(
                                data["Open"], data["High"], data["Low"], data["Close"]
                            )
                        ],
                        hoverinfo="text",
                        hoverlabel=dict(
                            namelength=0
                        ),
                        name=""             # remoce trace:0
                ),
                row=1,
                col=1
            )

            # RSI line
            fig.add_trace(
                pt.Scatter(
                    x=data.index,
                    y=data["RSI"],
                    mode="lines",
                    name="RSI (14)",
                    line=dict(
                        color="cyan",
                        width=2,
                        shape="spline",
                        smoothing=1.3
                    ),
                ),
                row=2,
                col=1
            )

            # RSI reference lines
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.4, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="red", opacity=0.4, row=2, col=1)

            # Layout polish
            fig.update_layout(
                height=chart_height,
                showlegend=True,
                xaxis_rangeslider_visible=False,
                margin=dict(t=60, b=40)
            )
            fig.update_yaxes(range=[0, 100], row=2, col=1)

            #UI settings
            fig.update_layout(
                height=chart_height,
                # Webull style hover
                hovermode="x unified",
                # 세로 가이드 라인
                xaxis=dict(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    showline=True,
                ),

                # Candlestick Y axis (right side)
                yaxis=dict(
                    side="right",
                    showgrid=True,
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    tickformat=".2f",
                ),

                # RSI Y axis (right side)
                yaxis2=dict(
                    side="right",
                    range=[0, 100],
                    showgrid=True,
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    tickformat=".1f",
                ),

                xaxis_rangeslider_visible=False,
                showlegend=False,
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error loading chart: {e}")
