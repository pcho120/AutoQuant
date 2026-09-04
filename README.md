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
- **Calibrated Direction Model**: Compares Logistic Regression, HistGradientBoosting, and Random Forest on out-of-sample Brier score
- **Independent Return Model**: Compares Ridge and HistGradientBoosting regression on out-of-sample MAE
- **Leakage-Safe Validation**: Expanding walk-forward splits with a five-trading-day purge between train, calibration, and test windows
- **Cached Results**: Supabase predictions are calculated by scheduled jobs; browser requests never train models
- **Explainability**: Displays observed technical/regime conditions, downside risk, model version, and timestamp-safe recent news

### Leverage Engine
- **Independent Strategy**: The Tripod engine does not call or reuse the individual-stock ML prediction pipeline
- **Regime Switching**: Uses NASDAQ-100/QQQ SMA-250, VIX MA-10, and 52-week drawdown to allocate to synthetic TQQQ, a 50/50 QQQ/QLD mix, or cash
- **Leakage-Safe Execution**: A signal calculated from day T close is executed at the configured T+1 open or close
- **Configurable Friction**: Commission, slippage, cash yield, and synthetic fund expense ratios are modeled explicitly
- **Risk Metrics**: Reports CAGR, MDD, Sharpe, Sortino, Ulcer Index, total return, and rebalance count

### Historical Data Pipeline
- **Market Collection**: Idempotent ten-year daily OHLCV collection from yfinance
- **News Collection**: Raw NewsAPI articles are stored independently from analysis
- **News Analysis**: Only unprocessed stored articles receive structured sentiment/event fields
- **Prediction Pipeline**: Daily feature/prediction updates and weekly model evaluation run without an open browser

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
│   └── leverage_engine.py # Independent Tripod strategy and backtest engine
├── ui/                  # Streamlit presentation layer (tab renderers)
├── tests/               # Unit tests with pytest (16 tests, 100% pass rate)
├── legacy/              # Original monolithic code (preserved for reference)
└── app.py               # DI container and routing shell
```

## Leverage Engine

The React `Leverage Engine` tab calls two independent FastAPI endpoints:

```text
GET  /api/leverage/signal?benchmark=QQQ
POST /api/leverage/backtest
```

Example backtest request:

```json
{
	"benchmark": "QQQ",
	"period": "max",
	"executionPrice": "close",
	"initialCapital": 100000,
	"commissionRate": 0.0005,
	"slippageRate": 0.0005,
	"cashAnnualYield": 0.0
}
```

The strategy keeps its previous `BULL` or `BEAR` state while price remains between 95% and 101% of SMA-250. Before the first directional observation, it starts conservatively from `BEAR`. `BULL` with VIX MA-10 below 28 and drawdown below 9% selects TQQQ. Risky `BULL`, or `BEAR` with VIX MA-10 below 18, selects 50% QQQ plus 50% QLD. The remaining `BEAR` regime selects cash.

Synthetic QLD/TQQQ series apply 2x/3x leverage to each daily selected-benchmark return and deduct daily fund expenses. They are research approximations and do not reproduce tracking error, financing spreads, distributions, closures, or intraday path dependence. Yahoo's QQQ history begins in 1999, so a QQQ run cannot provide a full 35-year test. Selecting `^NDX` uses the NASDAQ-100 price index as the 1x QQQ proxy and as the synthetic leverage source for the earlier period. Every response reports `one_x_proxy` and `data_period_years`; long-history index-proxy results must not be presented as investable ETF total returns.

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
| ML                 | scikit-learn 1.7, joblib |
| Testing            | pytest |
| TA Indicators      | pandas (rolling/ewm methods) |

---

## Historical Data Collection

The collection pipeline is independent from FastAPI, React, and Streamlit requests:

```text
External scheduler
	|-- collect_market_data ------> market_prices
	|-- collect_news -------------> news_articles (raw fields)
	|-- analyze_unprocessed_news -> news_articles (analysis fields)
	|-- build_prediction_features -> prediction_features
	|-- run_model_evaluation -----> model_evaluations + model_registry
	`-- run_predictions ----------> predictions -> FastAPI -> React
```

### Database prerequisite

Run the collector section of `db/create_tables.sql` in the Supabase SQL Editor before enabling the jobs. The live tables already contain the base columns, but the migration adds the constraints and metadata required by the implementation:

- Unique `market_prices(ticker, timestamp)` for candle upserts
- Unique `news_articles(ticker, url)` for article deduplication
- Unique `news_articles(ticker, provider_article_id)` when a URL is unavailable
- `provider_article_id`, `analyzed_at`, and `analysis_version` news columns
- Timestamp-safe `prediction_features` snapshots
- Versioned `model_registry`, `model_evaluations`, and `predictions`
- Query indexes for ticker/time lookups and screener ranking

Use a server-side Supabase key that has insert/update permission for these tables. Never expose this key to React.

### Configuration

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-server-side-key
NEWS_API_KEY=your-newsapi-key
COLLECTION_TICKERS=AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,SPY,QQQ,^VIX,XLK,XLC,XLY,XLF,XLE,XLV
MARKET_COLLECTION_PERIOD=10y
MARKET_COLLECTION_INTERVAL=1d
NEWS_COLLECTION_LOOKBACK_DAYS=2
COLLECTION_RETRY_ATTEMPTS=3
COLLECTION_RETRY_BASE_DELAY_SECONDS=1
COLLECTION_REQUEST_TIMEOUT_SECONDS=15
NEWS_ANALYSIS_BATCH_SIZE=100
CORS_ORIGINS=https://your-react-app.example.com
# React build variable when the API is hosted separately:
VITE_API_BASE_URL=https://your-fastapi.example.com
```

### Run one job

```powershell
.\env\Scripts\python.exe -m jobs.runner collect_market_data
.\env\Scripts\python.exe -m jobs.runner collect_news
.\env\Scripts\python.exe -m jobs.runner analyze_unprocessed_news
.\env\Scripts\python.exe -m jobs.runner build_prediction_features
.\env\Scripts\python.exe -m jobs.runner run_model_evaluation
.\env\Scripts\python.exe -m jobs.runner run_predictions
```

Each command is safe to run repeatedly. Market candles use database upsert. Duplicate news inserts use conflict-ignore semantics, preserving the first `collected_at`. Analysis selects only rows where `analyzed_at IS NULL` and updates the same row.

### Production schedule

Production scheduling is split by workload:

- `.github/workflows/data-collection.yml`: raw news collection and stored-news analysis every 8 hours at 00:17, 08:17, and 16:17 UTC. With the default 16 tickers, this uses 48 NewsAPI requests per day and stays within the Developer plan quota.
- `.github/workflows/market-predictions.yml`: triggered at 20:20 and 21:20 UTC on weekdays. An `America/New_York` gate permits only the run occurring at 16:20 local time, so DST is handled without seasonal cron edits. Order is market collection, feature build, cached prediction update.
- `.github/workflows/model-evaluation.yml`: Saturdays at 14:30 UTC. Rebuilds features, performs purged walk-forward evaluation, stores the new artifact/evaluation, and refreshes predictions.

Manual workflow dispatch bypasses the market-time gate. Configure repository secrets `SUPABASE_URL`, `SUPABASE_KEY`, and `NEWS_API_KEY`; optionally configure repository variable `COLLECTION_TICKERS`.

### Stored data semantics

Example market row:

```json
{
	"ticker": "AAPL",
	"timestamp": "2026-08-27T13:30:00+00:00",
	"open": 228.1,
	"high": 229.4,
	"low": 227.8,
	"close": 229.0,
	"volume": 1850240,
	"source": "yfinance",
	"timeframe": "1d"
}
```

Example analyzed news row fields:

```json
{
	"ticker": "AAPL",
	"published_at": "2026-08-27T12:00:00Z",
	"collected_at": "2026-08-27T12:04:15+00:00",
	"sentiment": 1.0,
	"event_type": "earnings",
	"materiality": 0.75,
	"impact": "positive",
	"impact_horizon": "1-20d",
	"analysis_version": "keyword-structured-v1.0.0"
}
```

The current analyzer is a deterministic structured baseline built on the existing keyword sentiment provider. It continues accumulating timestamped news, but news is deliberately excluded from ML features until enough point-in-time history exists. Detail responses only return news where `published_at <= prediction_timestamp`.

## Prediction methodology

The primary target horizon is five trading days:

```text
direction_up = Close[t+5] / Close[t] - 1 > 0
future_return = Close[t+5] / Close[t] - 1
```

Targets are created only in the training dataset and are never persisted in `prediction_features`. Features include RSI-14, MACD, moving averages, EMA, ATR, ADX, Bollinger width, relative volume, trailing returns, realized volatility, SPY/QQQ returns, sector ETF returns when mapped, and VIX level/change. Benchmark joins use only observations at or before each prediction timestamp.

Candidate classifiers are Logistic Regression, HistGradientBoostingClassifier, and RandomForestClassifier. Candidate regressors are Ridge and HistGradientBoostingRegressor. Selection uses validation Brier score and MAE respectively. Calibration requires at least 200 later validation observations containing both classes; otherwise the pipeline returns `Insufficient historical validation data`. It uses sigmoid calibration, or isotonic only when at least 1,000 calibration samples exist. Final metrics are computed on a separate purged test window.

`Probability Up` is the calibrated estimate that the return after five trading days will be positive. `Model Reliability` is out-of-sample Brier skill relative to historical prevalence; it is not another probability. Downside risk uses the 10th percentile of out-of-sample regression residuals. No arbitrary opportunity score is used.

Backtesting stores AUC, Brier score, log loss, directional accuracy, MAE, RMSE, mean realized returns for top 5/10/20 expected-return rankings, and SPY mean forward return. Production metrics are not claimed until real Supabase history has been collected and the evaluation job succeeds.

## Versioning and retraining

- Feature schema: `features-v1.0.0`
- Model family: `prediction-v1.0.0`; each trained artifact appends a UTC training timestamp and is immutable
- News analysis: `keyword-structured-v1.0.0`

Increment versions whenever feature definitions, targets, model families, or calibration methodology change. Existing prediction rows retain their original versions. To add securities, include the ticker plus required `SPY`, `QQQ`, `^VIX`, and mapped sector ETFs in `COLLECTION_TICKERS`. Run collection, feature generation, evaluation, then prediction in that order for initial setup.

## Production deployment

Apply `db/create_tables.sql` first. Use a server-side Supabase key only in FastAPI and GitHub Actions. Set `CORS_ORIGINS` on FastAPI to the deployed React origins and set `VITE_API_BASE_URL` at React build time when frontend and backend use different origins. The repository does not contain provider-specific FastAPI/React deployment manifests, so the hosting platform and public URLs remain deployment configuration.

Legacy market rows collected before the `timeframe` migration are marked `unknown` and intentionally excluded from model training. Run `collect_market_data` with `MARKET_COLLECTION_INTERVAL=1d` to seed trusted daily history; the collector writes the explicit `1d` provenance value.

## Limitations

- Real model quality, calibration, and ranking value cannot be reported until the live database contains enough daily history across the configured universe and `run_model_evaluation` completes.
- Historical NewsAPI coverage is not assumed; news is shown separately and excluded from training.
- The current primary horizon is 5D. The split and target code is configurable, but additional horizon artifacts and UI controls require separately validated model versions.
- Exchange holidays are represented by available market rows; the scheduler gate checks weekday/local hour but does not independently query an exchange holiday calendar.
