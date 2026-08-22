import streamlit as st
import pandas as pd
from domain.prediction import PredictionRequest
from components.ticker_search import get_ticker_list, render_ticker_search

def render_prediction_tab(prediction_service):
    st.header("Price Prediction")
    
    if "prediction_history" not in st.session_state:
        st.session_state.prediction_history = []
    
    st.info("AI-powered price prediction based on news sentiment and technical indicators.")

    if st.button("MACD golden cross", key="scan_macd_golden_cross"):
        with st.spinner("Scanning daily MACD signals..."):
            st.session_state.macd_scan_results = prediction_service.scan_macd_golden_crosses(
                get_ticker_list()
            )

    if "macd_scan_results" in st.session_state:
        st.subheader("MACD Golden Cross Candidates")
        scan_results = st.session_state.macd_scan_results
        if scan_results:
            scan_df = pd.DataFrame(scan_results)
            st.dataframe(
                scan_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Predicted Price (5d)": st.column_config.NumberColumn(format="$%.2f"),
                    "Expected Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                },
            )
        else:
            st.info("No current or approaching MACD golden crosses were found.")
    
    ticker = render_ticker_search(key="prediction_ticker", placeholder="Search ticker...").upper()
    horizon = st.selectbox("Prediction Horizon", options=["1d", "5d", "1mo"])
    
    submit = st.button("🚀 Predict Price")
        
    if submit:
        if ticker:
            with st.spinner(f"Predicting {ticker}..."):
                req = PredictionRequest(
                    ticker=ticker.upper(),
                    horizon=horizon,
                    include_news=True,
                    include_indicators=True,
                )
                result = prediction_service.predict_price(req)
                
                st.subheader(f"Results for {result.ticker}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Current Price", f"${result.current_price:.2f}")
                
                col2.metric(
                    "Predicted Price", 
                    f"${result.predicted_price:.2f}",
                    f"{result.change_dollars:+.2f} ({result.change_percent:+.2f}%)"
                )
                col3.metric("Confidence", f"{result.confidence:.1f}%")
                
                st.write("**Reasoning:**")
                st.markdown(result.reasoning)
                
                st.session_state.prediction_history.append({
                    "Ticker": result.ticker,
                    "Horizon": horizon,
                    "Current Price": f"${result.current_price:.2f}",
                    "Predicted Price": f"${result.predicted_price:.2f}",
                    "Confidence": f"{result.confidence:.1f}%",
                    "Reasoning": result.reasoning
                })
        else:
            st.error("Please enter a valid ticker symbol.")
            
    if st.session_state.prediction_history:
        st.subheader("Prediction History")
        history_df = pd.DataFrame(st.session_state.prediction_history)
        st.dataframe(history_df, use_container_width=True)
