from __future__ import annotations

from dataclasses import asdict, dataclass
from concurrent.futures import ThreadPoolExecutor
import math
from typing import Literal

import numpy as np
import pandas as pd


AllocationName = Literal["TQQQ", "QQQ_QLD", "CASH"]
ExecutionPrice = Literal["open", "close"]


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    execution_price: ExecutionPrice = "close"
    commission_rate: float = 0.0005
    slippage_rate: float = 0.0005
    cash_annual_yield: float = 0.0
    qld_expense_ratio: float = 0.0095
    tqqq_expense_ratio: float = 0.0082

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.execution_price not in {"open", "close"}:
            raise ValueError("execution_price must be 'open' or 'close'")
        for name in (
            "commission_rate", "slippage_rate", "cash_annual_yield",
            "qld_expense_ratio", "tqqq_expense_ratio",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True)
class PerformanceMetrics:
    cagr: float
    mdd: float
    sharpe_ratio: float
    sortino_ratio: float
    ulcer_index: float
    total_rebalances: int
    total_return: float
    start_date: str
    end_date: str


@dataclass(frozen=True)
class BacktestResult:
    metrics: PerformanceMetrics
    latest_signal: dict
    equity_curve: list[dict]
    trades: list[dict]

    def to_dict(self) -> dict:
        return {
            "metrics": asdict(self.metrics),
            "latest_signal": self.latest_signal,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }


def _normalize_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("Price history is empty")
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.columns = [str(column).lower() for column in data.columns]
    if "close" not in data.columns:
        raise ValueError("Price history must contain Close")
    if "open" not in data.columns:
        data["open"] = data["close"]
    data.index = pd.to_datetime(data.index, utc=True)
    return data.sort_index().loc[lambda value: ~value.index.duplicated(keep="last")]


def generate_synthetic_leverage_data(
    qqq: pd.DataFrame,
    leverage: float,
    annual_expense_ratio: float = 0.0,
    initial_price: float = 100.0,
) -> pd.DataFrame:
    """Build a daily-reset leveraged series from QQQ daily returns."""
    if leverage <= 0 or initial_price <= 0 or annual_expense_ratio < 0:
        raise ValueError("leverage and initial_price must be positive and expense ratio non-negative")
    source = _normalize_ohlc(qqq)
    daily_fee = annual_expense_ratio / 252.0
    daily_return = source["close"].pct_change(fill_method=None).fillna(0.0)
    leveraged_return = (leverage * daily_return - daily_fee).clip(lower=-0.999999)
    leveraged_return.iloc[0] = 0.0
    synthetic_close = initial_price * (1.0 + leveraged_return).cumprod()

    intraday_return = source["close"].div(source["open"]).sub(1.0)
    leveraged_intraday = (leverage * intraday_return - daily_fee / 2.0).clip(lower=-0.999999)
    synthetic_open = synthetic_close.div(1.0 + leveraged_intraday)
    synthetic_open.iloc[0] = initial_price

    result = pd.DataFrame(index=source.index)
    result["Open"] = synthetic_open
    result["Close"] = synthetic_close
    result["High"] = result[["Open", "Close"]].max(axis=1)
    result["Low"] = result[["Open", "Close"]].min(axis=1)
    result["Volume"] = 0
    return result


class TripodLeverageStrategy:
    """NASDAQ trend and VIX regime strategy with persistent neutral-zone state."""

    allocations: dict[AllocationName, dict[str, float]] = {
        "TQQQ": {"QQQ": 0.0, "QLD": 0.0, "TQQQ": 1.0, "CASH": 0.0},
        "QQQ_QLD": {"QQQ": 0.5, "QLD": 0.5, "TQQQ": 0.0, "CASH": 0.0},
        "CASH": {"QQQ": 0.0, "QLD": 0.0, "TQQQ": 0.0, "CASH": 1.0},
    }

    def calculate_signals(self, ndx: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
        ndx_data = _normalize_ohlc(ndx)
        vix_data = _normalize_ohlc(vix)
        signals = pd.DataFrame(index=ndx_data.index)
        signals["ndx_close"] = ndx_data["close"]
        signals["ndx_sma250"] = ndx_data["close"].rolling(250, min_periods=250).mean()
        signals["vix_ma10"] = vix_data["close"].rolling(10, min_periods=10).mean().reindex(
            signals.index, method="ffill",
        )
        high_52w = ndx_data["close"].rolling(250, min_periods=250).max()
        signals["mdd_52w"] = ndx_data["close"].div(high_52w).sub(1.0)

        states: list[str] = []
        previous_state = "BEAR"
        for close, average in zip(signals["ndx_close"], signals["ndx_sma250"]):
            if pd.isna(average):
                states.append("UNAVAILABLE")
            elif close > average * 1.01:
                previous_state = "BULL"
                states.append(previous_state)
            elif close < average * 0.95:
                previous_state = "BEAR"
                states.append(previous_state)
            else:
                states.append(previous_state)
        signals["state"] = states

        allocations: list[str | None] = []
        for state, vix_ma10, mdd_52w in zip(signals["state"], signals["vix_ma10"], signals["mdd_52w"]):
            if state == "UNAVAILABLE" or pd.isna(vix_ma10) or pd.isna(mdd_52w):
                allocations.append(None)
            elif state == "BULL" and vix_ma10 < 28 and abs(mdd_52w) < 0.09:
                allocations.append("TQQQ")
            elif state == "BULL":
                allocations.append("QQQ_QLD")
            elif vix_ma10 < 18:
                allocations.append("QQQ_QLD")
            else:
                allocations.append("CASH")
        signals["allocation"] = allocations
        for asset in ("QQQ", "QLD", "TQQQ", "CASH"):
            signals[f"weight_{asset.lower()}"] = signals["allocation"].map(
                lambda name, asset=asset: self.allocations[name][asset] if name else np.nan,
            )
        return signals

    def latest_signal(self, ndx: pd.DataFrame, vix: pd.DataFrame) -> dict:
        signals = self.calculate_signals(ndx, vix).dropna(subset=["allocation"])
        if signals.empty:
            raise ValueError("At least 250 aligned trading days are required")
        timestamp = signals.index[-1]
        row = signals.iloc[-1]
        allocation = str(row["allocation"])
        return {
            "as_of": timestamp.isoformat(),
            "state": row["state"],
            "allocation": allocation,
            "weights": self.allocations[allocation],
            "indicators": {
                "ndx_close": float(row["ndx_close"]),
                "ndx_sma250": float(row["ndx_sma250"]),
                "vix_ma10": float(row["vix_ma10"]),
                "mdd_52w": float(row["mdd_52w"]),
            },
        }


class LeverageBacktester:
    def __init__(self, strategy: TripodLeverageStrategy | None = None):
        self.strategy = strategy or TripodLeverageStrategy()

    def run(
        self,
        ndx: pd.DataFrame,
        vix: pd.DataFrame,
        qqq: pd.DataFrame,
        config: BacktestConfig | None = None,
        qld: pd.DataFrame | None = None,
        tqqq: pd.DataFrame | None = None,
    ) -> BacktestResult:
        settings = config or BacktestConfig()
        qqq_data = _normalize_ohlc(qqq)
        qld_data = _normalize_ohlc(qld) if qld is not None else _normalize_ohlc(
            generate_synthetic_leverage_data(qqq_data, 2.0, settings.qld_expense_ratio),
        )
        tqqq_data = _normalize_ohlc(tqqq) if tqqq is not None else _normalize_ohlc(
            generate_synthetic_leverage_data(qqq_data, 3.0, settings.tqqq_expense_ratio),
        )
        signals = self.strategy.calculate_signals(ndx, vix)
        price_column = settings.execution_price
        prices = pd.concat({
            "QQQ": qqq_data[price_column],
            "QLD": qld_data[price_column],
            "TQQQ": tqqq_data[price_column],
        }, axis=1).dropna()
        frame = signals.join(prices, how="inner").dropna(subset=["allocation"])
        if len(frame) < 2:
            raise ValueError("Insufficient aligned history for a backtest")

        asset_returns = frame[["QQQ", "QLD", "TQQQ"]].pct_change(fill_method=None).fillna(0.0)
        cash_daily_return = (1.0 + settings.cash_annual_yield) ** (1.0 / 252.0) - 1.0
        target_weights = frame[[
            "weight_qqq", "weight_qld", "weight_tqqq", "weight_cash",
        ]].shift(1)
        target_weights.columns = ["QQQ", "QLD", "TQQQ", "CASH"]

        equity = settings.initial_capital
        current_weights = pd.Series({asset: 0.0 for asset in ("QQQ", "QLD", "TQQQ", "CASH")})
        current_weights["CASH"] = 1.0
        curve: list[dict] = []
        trades: list[dict] = []
        daily_returns: list[float] = []
        cost_rate = settings.commission_rate + settings.slippage_rate

        for position, timestamp in enumerate(frame.index):
            starting_equity = equity
            if position:
                returns = asset_returns.loc[timestamp]
                gross_return = float(
                    current_weights["QQQ"] * returns["QQQ"]
                    + current_weights["QLD"] * returns["QLD"]
                    + current_weights["TQQQ"] * returns["TQQQ"]
                    + current_weights["CASH"] * cash_daily_return
                )
                equity *= 1.0 + gross_return
            else:
                gross_return = 0.0

            desired = target_weights.loc[timestamp]
            transaction_cost = 0.0
            if not desired.isna().any() and not np.allclose(desired.values, current_weights.values):
                turnover = float((desired - current_weights).abs().sum())
                transaction_cost = equity * turnover * cost_rate
                equity -= transaction_cost
                signal_timestamp = frame.index[position - 1]
                trades.append({
                    "signal_date": signal_timestamp.isoformat(),
                    "execution_date": timestamp.isoformat(),
                    "execution_price": settings.execution_price,
                    "allocation": str(frame.loc[signal_timestamp, "allocation"]),
                    "turnover": turnover,
                    "cost": transaction_cost,
                })
                current_weights = desired.copy()

            net_return = equity / starting_equity - 1.0
            daily_returns.append(net_return)
            curve.append({
                "date": timestamp.isoformat(),
                "equity": equity,
                "drawdown": 0.0,
                "allocation": self._allocation_name(current_weights),
            })

        equity_series = pd.Series([point["equity"] for point in curve], index=frame.index)
        drawdown = equity_series.div(equity_series.cummax()).sub(1.0)
        for point, value in zip(curve, drawdown):
            point["drawdown"] = float(value)
        metrics = self._metrics(equity_series, pd.Series(daily_returns, index=frame.index), len(trades))
        latest_signal = self.strategy.latest_signal(ndx, vix)
        return BacktestResult(metrics, latest_signal, curve, trades)

    @staticmethod
    def _allocation_name(weights: pd.Series) -> str:
        if weights["TQQQ"] > 0.99:
            return "TQQQ"
        if weights["CASH"] > 0.99:
            return "CASH"
        return "QQQ_QLD"

    @staticmethod
    def _metrics(equity: pd.Series, returns: pd.Series, trade_count: int) -> PerformanceMetrics:
        elapsed_days = max((equity.index[-1] - equity.index[0]).days, 1)
        years = elapsed_days / 365.25
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)
        drawdown = equity.div(equity.cummax()).sub(1.0)
        volatility = float(returns.std(ddof=0))
        sharpe = float(returns.mean() / volatility * math.sqrt(252)) if volatility > 0 else 0.0
        downside = returns.clip(upper=0.0)
        downside_deviation = float(np.sqrt(np.mean(np.square(downside))))
        sortino = float(returns.mean() / downside_deviation * math.sqrt(252)) if downside_deviation > 0 else 0.0
        return PerformanceMetrics(
            cagr=cagr,
            mdd=float(drawdown.min()),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            ulcer_index=float(np.sqrt(np.mean(np.square(drawdown)))) * 100.0,
            total_rebalances=trade_count,
            total_return=total_return,
            start_date=equity.index[0].isoformat(),
            end_date=equity.index[-1].isoformat(),
        )


class LeverageEngineService:
    """Application boundary for loading market data and running the leverage engine."""

    def __init__(self, market):
        self.market = market
        self.strategy = TripodLeverageStrategy()
        self.backtester = LeverageBacktester(self.strategy)

    def get_signal(self, benchmark: str = "QQQ") -> dict:
        histories = self._load_histories((benchmark, "^VIX"), period="2y")
        return {
            **self.strategy.latest_signal(histories[benchmark], histories["^VIX"]),
            "benchmark": benchmark,
        }

    def run_backtest(
        self,
        benchmark: str = "QQQ",
        period: str = "max",
        config: BacktestConfig | None = None,
    ) -> dict:
        tickers = tuple(dict.fromkeys((benchmark, "^VIX")))
        histories = self._load_histories(tickers, period=period)
        result = self.backtester.run(
            histories[benchmark], histories["^VIX"], histories[benchmark], config,
        ).to_dict()
        start = pd.Timestamp(result["metrics"]["start_date"])
        end = pd.Timestamp(result["metrics"]["end_date"])
        result["benchmark"] = benchmark
        result["one_x_proxy"] = benchmark
        result["data_period_years"] = round((end - start).days / 365.25, 2)
        result["synthetic_assets"] = ["QLD", "TQQQ"]
        return result

    def _load_histories(self, tickers: tuple[str, ...], period: str) -> dict[str, pd.DataFrame]:
        with ThreadPoolExecutor(max_workers=len(tickers)) as executor:
            futures = {
                ticker: executor.submit(self.market.fetch_historical_data, ticker, period, "1d")
                for ticker in tickers
            }
            histories = {ticker: future.result() for ticker, future in futures.items()}
        missing = [ticker for ticker, history in histories.items() if history is None or history.empty]
        if missing:
            raise ValueError(f"No daily market data available for: {', '.join(missing)}")
        return histories