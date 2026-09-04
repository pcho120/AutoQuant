from functools import lru_cache
from datetime import datetime, timezone
import math
import os
from typing import Annotated, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from adapters import DBClient, MarketDataAdapter, NewsProvider, WebullPortfolioAdapter
from adapters.collection_repository import CollectionRepository
from domain.position import Order, Position
from domain.prediction import PredictionRequest
from services import PredictionService, TradingService
from services.leverage_engine import BacktestConfig, LeverageEngineService


ALLOWED_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y"}
ALLOWED_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"}
PREDICTION_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JNJ", "V",
    "WMT", "JPM", "MA", "PG", "DIS", "ADBE", "CRM", "NFLX", "PYPL", "INTC",
    "AMD", "MU", "QCOM", "IBM", "CSCO", "ORCL", "SAP", "TXN", "STM", "GOOG",
    "BABA", "JD", "BIDU", "NTES", "SPY", "QQQ", "IVV", "VOO", "VTI", "BND",
    "AGG", "GLD", "TLT", "LQD", "F", "GM", "TM", "HMC", "TSM", "UNH",
    "CVS", "ABT", "PFE", "MRK", "GILD", "BIIB", "REGN", "VEEV", "ILMN", "CRSP",
    "EDIT", "BEAM", "XOM", "CVX", "COP", "EOG", "PSX", "MPC", "VLO", "HES",
    "OKE", "EQT", "BAC", "WFC", "GS", "BLK", "SCHW", "CME", "ICE", "CBOE",
    "MSCI", "SPGI", "SO", "NEE", "DUK", "EXC", "AEP", "XEL", "D", "PPL",
    "ETR", "ED", "PLD", "AMT", "CCI", "EQIX", "DLR", "VICI", "SBAC", "STAG", "PEG",
]
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app = FastAPI(title="AutoQuant Market API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST"],
    allow_headers=["*"],
)


@lru_cache
def get_db_client() -> DBClient:
    return DBClient()


@lru_cache
def get_market_data() -> MarketDataAdapter:
    return MarketDataAdapter()


@lru_cache
def get_trading_service() -> TradingService:
    return TradingService(get_db_client(), get_market_data())


@lru_cache
def get_prediction_service() -> PredictionService:
    return PredictionService(get_market_data(), NewsProvider(os.getenv("NEWS_API_KEY", "")))


@lru_cache
def get_leverage_engine() -> LeverageEngineService:
    return LeverageEngineService(get_market_data())


def get_webull_portfolio() -> WebullPortfolioAdapter:
    return WebullPortfolioAdapter()


@lru_cache
def get_collection_repository() -> CollectionRepository:
    return CollectionRepository()


class PositionInput(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    buyPrice: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        return ticker


class PortfolioInput(BaseModel):
    positions: list[PositionInput]


class PaperPositionInput(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    buyPrice: float = Field(ge=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        return ticker


class PaperPortfolioInput(BaseModel):
    positions: list[PaperPositionInput]


class OrderInput(BaseModel):
    ticker: str
    action: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    cashBalance: float = Field(ge=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        return ticker


class PredictionInput(BaseModel):
    ticker: str
    horizon: Literal["1d", "5d", "1mo"]
    includeNews: bool = True
    includeIndicators: bool = True

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        return ticker


class LeverageBacktestInput(BaseModel):
    benchmark: Literal["QQQ", "^NDX"] = "QQQ"
    period: Literal["2y", "5y", "10y", "max"] = "max"
    executionPrice: Literal["open", "close"] = "close"
    initialCapital: float = Field(default=100_000, gt=0)
    commissionRate: float = Field(default=0.0005, ge=0, le=0.05)
    slippageRate: float = Field(default=0.0005, ge=0, le=0.05)
    cashAnnualYield: float = Field(default=0.0, ge=0, le=1)


def _number(value) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def build_market_payload(
    ticker: str,
    period: str,
    interval: str,
    history: pd.DataFrame,
) -> dict:
    if history is None or history.empty:
        raise ValueError(f"No market data is available for {ticker}")

    data = history.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required_columns = {"Open", "High", "Low", "Close", "Volume"}
    if not required_columns.issubset(data.columns):
        raise ValueError("Market data is missing required OHLCV columns")

    close = data["Close"].astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    average_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, float("nan"))
    data["RSI"] = 100 - (100 / (1 + relative_strength))
    data.loc[(average_loss == 0) & (average_gain > 0), "RSI"] = 100
    data.loc[(average_loss == 0) & (average_gain == 0), "RSI"] = 50

    data["MACD"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    data["MACDSignal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACDHistogram"] = data["MACD"] - data["MACDSignal"]

    candles = []
    volumes = []
    rsi = []
    macd = []
    for timestamp, row in data.iterrows():
        time = int(pd.Timestamp(timestamp).timestamp())
        candles.append({
            "time": time,
            "open": _number(row["Open"]),
            "high": _number(row["High"]),
            "low": _number(row["Low"]),
            "close": _number(row["Close"]),
        })
        volumes.append({
            "time": time,
            "value": _number(row["Volume"]),
            "color": "#1f9d78" if row["Close"] >= row["Open"] else "#d9534f",
        })
        rsi_value = _number(row["RSI"])
        if rsi_value is not None:
            rsi.append({"time": time, "value": rsi_value})
        macd.append({
            "time": time,
            "macd": _number(row["MACD"]),
            "signal": _number(row["MACDSignal"]),
            "histogram": _number(row["MACDHistogram"]),
        })

    return {
        "ticker": ticker.upper(),
        "period": period,
        "interval": interval,
        "lastUpdated": pd.Timestamp.now(tz="UTC").isoformat(),
        "candles": candles,
        "volume": volumes,
        "rsi": rsi,
        "macd": macd,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/portfolio/{user_id}")
def portfolio(user_id: str) -> dict:
    positions = get_db_client().fetch_positions(user_id, table_name="portfolio")
    prices = get_market_data().fetch_current_prices([position.ticker for position in positions])
    return {
        "userId": user_id,
        "positions": [
            {
                "ticker": position.ticker,
                "quantity": position.quantity,
                "buyPrice": position.buy_price,
                "currentPrice": prices.get(position.ticker, position.current_price),
            }
            for position in positions
        ],
    }


@app.put("/api/portfolio/{user_id}")
def save_portfolio(user_id: str, payload: PortfolioInput) -> dict:
    positions = [
        Position(
            ticker=item.ticker,
            quantity=item.quantity,
            buy_price=item.buyPrice,
            current_price=0.0,
        )
        for item in payload.positions
    ]
    if get_db_client().save_positions(user_id, positions, table_name="portfolio") is False:
        raise HTTPException(status_code=502, detail="Unable to save portfolio to Supabase")
    return {"userId": user_id, "saved": len(positions)}


@app.post("/api/portfolio/{user_id}/sync-webull")
def sync_webull_portfolio(user_id: str) -> dict:
    try:
        webull_portfolio = get_webull_portfolio().fetch_portfolio()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch portfolio from Webull") from exc

    if get_db_client().save_positions(
        user_id,
        webull_portfolio.positions,
        table_name="portfolio",
    ) is False:
        raise HTTPException(status_code=502, detail="Unable to save Webull portfolio to Supabase")

    return {
        "userId": user_id,
        "accounts": webull_portfolio.account_count,
        "synced": len(webull_portfolio.positions),
    }


@app.get("/api/paper-trading/{user_id}")
def paper_portfolio(user_id: str) -> dict:
    positions = get_db_client().fetch_positions(user_id, table_name="paper_portfolio")
    prices = get_market_data().fetch_current_prices([position.ticker for position in positions])
    return {
        "userId": user_id,
        "positions": [
            {
                "ticker": position.ticker,
                "quantity": position.quantity,
                "buyPrice": position.buy_price,
                "currentPrice": prices.get(position.ticker, position.current_price),
            }
            for position in positions
        ],
    }


@app.put("/api/paper-trading/{user_id}")
def save_paper_portfolio(user_id: str, payload: PaperPortfolioInput) -> dict:
    positions = [
        Position(item.ticker, item.quantity, item.buyPrice, 0.0)
        for item in payload.positions
    ]
    if get_db_client().save_positions(user_id, positions, table_name="paper_portfolio") is False:
        raise HTTPException(status_code=502, detail="Unable to save paper portfolio to Supabase")
    return {"userId": user_id, "saved": len(positions)}


@app.post("/api/paper-trading/{user_id}/orders")
def execute_paper_order(user_id: str, payload: OrderInput) -> dict:
    order = Order(
        ticker=payload.ticker,
        action=payload.action,
        quantity=payload.quantity,
        price=payload.price,
        timestamp=datetime.now(),
    )
    result = get_trading_service().execute_order(user_id, order, payload.cashBalance)
    if result.get("status") != "SUCCESS":
        raise HTTPException(status_code=400, detail=result.get("reason", "Order failed"))
    return result


@app.get("/api/leverage/signal")
def leverage_signal(benchmark: Literal["QQQ", "^NDX"] = "QQQ") -> dict:
    try:
        return get_leverage_engine().get_signal(benchmark)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to calculate leverage signal") from exc


@app.post("/api/leverage/backtest")
def leverage_backtest(payload: LeverageBacktestInput) -> dict:
    config = BacktestConfig(
        initial_capital=payload.initialCapital,
        execution_price=payload.executionPrice,
        commission_rate=payload.commissionRate,
        slippage_rate=payload.slippageRate,
        cash_annual_yield=payload.cashAnnualYield,
    )
    try:
        return get_leverage_engine().run_backtest(payload.benchmark, payload.period, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to run leverage backtest") from exc


def _prediction_payload(row: dict, news: list[dict] | None = None) -> dict:
    timestamp = pd.Timestamp(row["prediction_timestamp"])
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    age = pd.Timestamp.now(tz="UTC") - timestamp.tz_convert("UTC")
    return {
        "ticker": row["ticker"],
        "horizon": row["horizon"],
        "predictionTimestamp": timestamp.isoformat(),
        "currentPrice": row["current_price"],
        "expectedReturn": row.get("expected_return"),
        "predictedPrice": row.get("predicted_price"),
        "probabilityUp": row.get("probability_up"),
        "downsideRisk": row.get("downside_risk"),
        "riskReward": row.get("risk_reward"),
        "signal": row["signal"],
        "modelReliability": row.get("reliability"),
        "reliabilityStatus": row["reliability_status"],
        "modelVersion": row["model_version"],
        "featureVersion": row["feature_version"],
        "stale": age > pd.Timedelta(days=4),
        "explanation": row.get("explanation") or {},
        "recentNews": news or [],
    }


def _prediction_read_error(exc: Exception) -> HTTPException:
    if getattr(exc, "code", None) == "PGRST205":
        return HTTPException(
            status_code=503,
            detail="Prediction tables are not initialized in Supabase. Apply db/create_tables.sql.",
        )
    return HTTPException(status_code=502, detail="Unable to read cached prediction")


@app.post("/api/predictions")
def predict_price(payload: PredictionInput) -> dict:
    try:
        row = get_collection_repository().fetch_latest_prediction(payload.ticker, payload.horizon)
    except Exception as exc:
        raise _prediction_read_error(exc) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Insufficient historical validation data")
    news = get_collection_repository().fetch_recent_news(payload.ticker, row["prediction_timestamp"])
    return _prediction_payload(row, news)


@app.get("/api/predictions/screener")
def prediction_screener(
    sort: Literal["expected_return", "probability_up"] = "expected_return",
    horizon: Literal["5d"] = "5d",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    try:
        rows = get_collection_repository().fetch_latest_predictions(horizon)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to read prediction screener") from exc
    eligible = [row for row in rows if row.get(sort) is not None]
    eligible.sort(key=lambda row: row[sort], reverse=True)
    return {"sort": sort, "horizon": horizon, "results": [_prediction_payload(row) for row in eligible[:limit]]}


@app.get("/api/predictions/{ticker}")
def prediction_detail(ticker: str, horizon: Literal["5d"] = "5d") -> dict:
    normalized = ticker.strip().upper()
    if not normalized or len(normalized) > 10 or not normalized.replace(".", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid ticker")
    try:
        row = get_collection_repository().fetch_latest_prediction(normalized, horizon)
        if not row:
            raise HTTPException(status_code=404, detail="Insufficient historical validation data")
        news = get_collection_repository().fetch_recent_news(normalized, row["prediction_timestamp"])
        return _prediction_payload(row, news)
    except HTTPException:
        raise
    except Exception as exc:
        raise _prediction_read_error(exc) from exc


@app.post("/api/predictions/scan-macd")
def scan_macd_golden_crosses() -> dict:
    try:
        results = get_prediction_service().scan_macd_golden_crosses(PREDICTION_TICKERS)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to scan MACD signals") from exc
    return {
        "results": [
            {
                "ticker": row["Ticker"],
                "name": row["Name"],
                "status": row["Status"],
                "currentPrice": row["Current Price"],
                "predictedPrice": row["Predicted Price (5d)"],
                "expectedChangePercent": row["Expected Change (%)"],
            }
            for row in results
        ],
    }


@app.get("/api/tickers")
def search_tickers(q: Annotated[str, Query(min_length=1, max_length=50)]) -> dict:
    try:
        results = get_market_data().search_tickers(q)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to search tickers") from exc
    return {"results": results}


@app.get("/api/market/{ticker}")
def market_data(
    ticker: str,
    period: Annotated[str, Query()] = "1mo",
    interval: Annotated[str, Query()] = "5m",
) -> dict:
    if period not in ALLOWED_PERIODS or interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="Unsupported period or interval")

    try:
        history = get_market_data().fetch_historical_data(ticker.upper(), period, interval)
        return build_market_payload(ticker, period, interval, history)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to fetch Yahoo Finance data") from exc