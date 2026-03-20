import streamlit as st
import pandas as pd
from domain.prediction import PredictionRequest
from components.ticker_search import render_ticker_search

def render_prediction_tab(prediction_service):
    st.header("Price Prediction")
    
    if "prediction_history" not in st.session_state:
        st.session_state.prediction_history = []
    
    st.info("AI-powered price prediction based on news sentiment and technical indicators.")
    
    ticker = render_ticker_search(key="prediction_ticker", placeholder="Search ticker...").upper()
    horizon = st.selectbox("Prediction Horizon", options=["1d", "5d", "1mo"])
    
    submit = st.button("🚀 Predict Price")
        
    if submit:
        if ticker:
            with st.spinner(f"Predicting {ticker}..."):
                req = PredictionRequest(ticker=ticker.upper(), horizon=horizon)
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
