from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


FEATURE_VERSION = "features-v1.0.0"
MINIMUM_HISTORY = 200

SECTOR_ETFS = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "GOOGL": "XLC",
    "GOOG": "XLC", "META": "XLC", "AMZN": "XLY", "TSLA": "XLY",
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "XOM": "XLE",
    "CVX": "XLE", "JNJ": "XLV", "PFE": "XLV", "UNH": "XLV",
}


@dataclass(frozen=True)
class FeatureBuildResult:
    ticker: str
    rows: list[dict]
    skipped_reason: str | None = None


class FeatureEngine:
    """Builds causal daily features; every row depends only on rows at or before it."""

    def build(
        self,
        ticker: str,
        prices: pd.DataFrame,
        spy: pd.DataFrame,
        qqq: pd.DataFrame,
        vix: pd.DataFrame,
        sector: pd.DataFrame | None = None,
        sector_etf: str | None = None,
    ) -> FeatureBuildResult:
        data = self._normalize(prices)
        if len(data) < MINIMUM_HISTORY:
            return FeatureBuildResult(ticker, [], f"requires at least {MINIMUM_HISTORY} daily candles")

        close = data["close"]
        high = data["high"]
        low = data["low"]
        volume = data["volume"]

        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        strength = gain / loss.replace(0, np.nan)
        data["rsi_14"] = 100 - (100 / (1 + strength))
        data.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100.0

        data["ema_12"] = close.ewm(span=12, adjust=False).mean()
        data["ema_26"] = close.ewm(span=26, adjust=False).mean()
        data["macd"] = data["ema_12"] - data["ema_26"]
        data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
        data["macd_histogram"] = data["macd"] - data["macd_signal"]
        for window in (20, 50, 200):
            data[f"sma_{window}"] = close.rolling(window, min_periods=window).mean()

        previous_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ], axis=1).max(axis=1)
        data["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        data["atr_pct"] = data["atr_14"] / close
        data["adx_14"] = self._adx(high, low, true_range)

        rolling_mean = close.rolling(20, min_periods=20).mean()
        rolling_std = close.rolling(20, min_periods=20).std(ddof=0)
        data["bb_width"] = (4 * rolling_std) / rolling_mean
        data["relative_volume"] = volume / volume.rolling(20, min_periods=20).mean()
        data["return_1d"] = close.pct_change(1, fill_method=None)
        data["return_5d"] = close.pct_change(5, fill_method=None)
        data["return_20d"] = close.pct_change(20, fill_method=None)
        data["realized_volatility_20d"] = data["return_1d"].rolling(20).std(ddof=0) * math.sqrt(252)

        data = self._join_benchmark(data, spy, "spy")
        data = self._join_benchmark(data, qqq, "qqq")
        data = self._join_vix(data, vix)
        selected_sector = sector_etf or SECTOR_ETFS.get(ticker.upper())
        if sector is not None and selected_sector:
            data = self._join_benchmark(data, sector, "sector")
        else:
            data["sector_return_5d"] = np.nan
            data["sector_return_20d"] = np.nan
        data["sector_etf"] = selected_sector
        data["market_trend"] = np.select(
            [
                (data["spy_return_20d"] > 0) & (data["qqq_return_20d"] > 0),
                (data["spy_return_20d"] < 0) & (data["qqq_return_20d"] < 0),
            ],
            ["bullish", "bearish"],
            default="mixed",
        )

        feature_columns = [
            "rsi_14", "macd", "macd_signal", "macd_histogram", "sma_20", "sma_50", "sma_200",
            "ema_12", "ema_26", "atr_14", "atr_pct", "adx_14", "bb_width", "relative_volume",
            "return_1d", "return_5d", "return_20d", "realized_volatility_20d", "spy_return_5d",
            "spy_return_20d", "qqq_return_5d", "qqq_return_20d", "vix", "vix_change",
        ]
        if sector is not None and selected_sector:
            feature_columns.extend(["sector_return_5d", "sector_return_20d"])
        complete = data.dropna(subset=feature_columns)
        rows = []
        for timestamp, row in complete.iterrows():
            values = {column: float(row[column]) for column in feature_columns}
            rows.append({
                "ticker": ticker.upper(),
                "timestamp": timestamp.isoformat(),
                **values,
                "sector_etf": selected_sector,
                "market_trend": str(row["market_trend"]),
                "feature_version": FEATURE_VERSION,
            })
        return FeatureBuildResult(ticker.upper(), rows)

    @staticmethod
    def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        data = frame.copy()
        data.columns = [str(column).lower() for column in data.columns]
        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
            data = data.set_index("timestamp")
        else:
            data.index = pd.to_datetime(data.index, utc=True)
        return data.sort_index().loc[lambda value: ~value.index.duplicated(keep="last")]

    @staticmethod
    def _adx(high: pd.Series, low: pd.Series, true_range: pd.Series) -> pd.Series:
        upward = high.diff()
        downward = -low.diff()
        plus_dm = upward.where((upward > downward) & (upward > 0), 0.0)
        minus_dm = downward.where((downward > upward) & (downward > 0), 0.0)
        atr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        return dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    def _join_benchmark(self, data: pd.DataFrame, benchmark: pd.DataFrame, prefix: str) -> pd.DataFrame:
        normalized = self._normalize(benchmark)
        returns = pd.DataFrame(index=normalized.index)
        returns[f"{prefix}_return_5d"] = normalized["close"].pct_change(5, fill_method=None)
        returns[f"{prefix}_return_20d"] = normalized["close"].pct_change(20, fill_method=None)
        return data.join(returns.reindex(data.index, method="ffill"))

    def _join_vix(self, data: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
        normalized = self._normalize(vix)
        values = pd.DataFrame(index=normalized.index)
        values["vix"] = normalized["close"]
        values["vix_change"] = normalized["close"].pct_change(5, fill_method=None)
        return data.join(values.reindex(data.index, method="ffill"))