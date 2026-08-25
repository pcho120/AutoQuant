from functools import lru_cache
import math
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from adapters import DBClient, MarketDataAdapter
from domain.position import Position


ALLOWED_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y"}
ALLOWED_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d"}

app = FastAPI(title="AutoQuant Market API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "PUT"],
    allow_headers=["*"],
)


@lru_cache
def get_db_client() -> DBClient:
    return DBClient()


@lru_cache
def get_market_data() -> MarketDataAdapter:
    return MarketDataAdapter()


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
    get_db_client().save_positions(user_id, positions, table_name="portfolio")
    return {"userId": user_id, "saved": len(positions)}


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