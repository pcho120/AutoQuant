import streamlit as st
import pandas as pd
import plotly.express as px

def render_portfolio_tab(portfolio_service, user_id: str = "default_user"):
    st.header("Portfolio Management")

    col1, col2 = st.columns([1, 1])
    with col1:
        # Manual refresh button invokes st.cache_data.clear()
        if st.button("🔄 Refresh Market Data"):
            st.cache_data.clear()
            st.rerun()

    # Fetch portfolio using service
    portfolio = portfolio_service.get_portfolio(user_id)
    
    st.subheader("Your Positions")
    
    # Prepare DataFrame for editing
    data = []
    for p in portfolio.positions:
        data.append({
            "Ticker": p.ticker,
            "Quantity": p.quantity,
            "Buy Price": p.buy_price,
            "Current Price": p.current_price
        })
        
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=["Ticker", "Quantity", "Buy Price", "Current Price"])

    # Render portfolio table with st.data_editor
    # Enforce conditional refresh: on_change=None to prevent state-loss during cell edits
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        on_change=None,
        key="portfolio_editor"
    )

    # Save button triggers data persistence then st.rerun()
    if st.button("💾 Save"):
        portfolio_service.update_positions(user_id, edited_df)
        st.success("Portfolio updated successfully!")
        st.rerun()

    st.subheader("Asset Allocation")
    
    # Render allocation pie chart display (plotly)
    allocations = portfolio_service.calculate_allocation(portfolio)
    
    if allocations:
        alloc_df = pd.DataFrame(list(allocations.items()), columns=["Ticker", "Allocation (%)"])
        fig = px.pie(
            alloc_df, 
            values="Allocation (%)", 
            names="Ticker", 
            title="Portfolio Allocation",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active positions to display allocation.")
