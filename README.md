# 📊 AutoQuant: AI Portfolio Optimizer

**AutoQuant** is a Streamlit-based portfolio management and analysis platform with AI-powered price predictions, paper trading simulation, and real-time market data integration.

---

## 🚀 Features

### Portfolio Management
- **Editable Portfolio Table**: Manage tickers, quantities, and buy prices with live market data updates
- **Automatic Allocation Calculation**: Real-time portfolio allocation percentages and P/L tracking
- **Interactive Charting**: Plotly-powered visualizations with allocation breakdown

### Paper Trading
- **Simulated Order Execution**: Test BUY/SELL strategies with $100k virtual cash
- **Transaction Fee Modeling**: 0.1% fee calculation on all trades
- **Order History Tracking**: Persistent order records with timestamps

### AI Prediction Engine
- **Multi-Factor Analysis**: Combines technical indicators (RSI, MACD, MA) and news sentiment
- **Confidence Scoring**: Bounded confidence metrics (0-85%) based on signal strength
- **Explainable Reasoning**: Detailed breakdown of prediction components and signals

### Settings & Configuration
- **Supabase Integration**: Persistent storage for positions and orders
- **NewsAPI Integration**: Real-time financial news with sentiment analysis

---

## 🏗️ Architecture

AutoQuant follows a **layered clean architecture** pattern for maintainability and testability:

```
AutoQuant/
├── domain/              # Core business entities (Position, Order, PredictionRequest)
├── adapters/            # External service wrappers (MarketData, DB, NewsProvider)
├── services/            # Business logic layer (Portfolio, Trading, Prediction services)
├── ui/                  # Streamlit presentation layer (tab renderers)
├── tests/               # Unit tests with pytest (16 tests, 100% pass rate)
├── legacy/              # Original monolithic code (preserved for reference)
└── app.py               # DI container and routing shell
```

**Design Principles:**
- **Dependency Injection**: Services receive adapters via constructor injection
- **Separation of Concerns**: UI, business logic, and data access strictly separated
- **Testability**: All services unit-tested with mocked dependencies
- **Caching**: Streamlit `@st.cache_resource` for singleton adapters, `@st.cache_data(ttl=300)` for market data

---

## 🧰 Tech Stack

| Category           | Technology               |
|--------------------|--------------------------|
| Language           | Python 3.11+             |
| Web Framework      | [Streamlit](https://streamlit.io) |
| Visualization      | [Plotly](https://plotly.com/python/) |
| Financial Data     | [yfinance](https://github.com/ranaroussi/yfinance) |
| News API           | [NewsAPI.org](https://newsapi.org) |
| Database           | [Supabase](https://supabase.com) (PostgreSQL) |
| Testing            | pytest, pytest-mock |
| TA Indicators      | pandas (rolling/ewm methods) |

---
