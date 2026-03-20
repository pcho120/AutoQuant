import streamlit as st
from adapters import MarketDataAdapter, DBClient, NewsProvider
from services import PortfolioService, TradingService, PredictionService
from ui import (
    render_portfolio_tab,
    render_trading_tab,
    render_prediction_tab,
    render_settings_tab,
)


@st.cache_resource
def get_db_client():
    """Singleton database adapter instance."""
    return DBClient()


@st.cache_resource
def get_market_data_adapter():
    """Singleton market data adapter instance."""
    return MarketDataAdapter()


@st.cache_resource
def get_news_provider():
    """Singleton news provider adapter instance."""
    api_key = st.secrets.get("newsapi", {}).get("key", "")
    return NewsProvider(api_key)


@st.cache_resource
def get_portfolio_service():
    """Portfolio service with injected dependencies."""
    db = get_db_client()
    market = get_market_data_adapter()
    return PortfolioService(db, market)


@st.cache_resource
def get_trading_service():
    """Trading service with injected dependencies."""
    db = get_db_client()
    market = get_market_data_adapter()
    return TradingService(db, market)


@st.cache_resource
def get_prediction_service():
    """Prediction service with injected dependencies."""
    market = get_market_data_adapter()
    news = get_news_provider()
    return PredictionService(market, news)


st.set_page_config(page_title="AutoQuant", layout="wide")
st.markdown("# AutoQuant")

portfolio_service = get_portfolio_service()
trading_service = get_trading_service()
prediction_service = get_prediction_service()

tab1, tab2, tab3, tab4 = st.tabs(["Portfolio", "Paper Trading", "AI Prediction", "Settings"])

with tab1:
    render_portfolio_tab(portfolio_service)

with tab2:
    render_trading_tab(trading_service)

with tab3:
    render_prediction_tab(prediction_service)

with tab4:
    render_settings_tab()
