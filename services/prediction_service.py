from domain.prediction import PredictionRequest, PredictionResult
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd


class PredictionService:
    """
    Service for stock price prediction.
    
    NOTE: Real AI logic and technical indicators will be implemented in Phase 5 (Tasks 14-15).
    This stub provides a deterministic baseline for testing downstream components.
    """

    def __init__(self, market, news):
        """
        Initialize the prediction service with market and news adapters.

        Args:
            market: MarketDataAdapter instance for fetching current prices
            news: NewsProvider instance for fetching news data
        """
        self.market = market
        self.news = news

    def predict_price(self, request: PredictionRequest) -> PredictionResult:
        raise RuntimeError(
            "Rule-based price prediction has been retired; read a validated cached prediction from Supabase"
        )

    def calculate_indicators(self, ticker: str) -> dict:
        """
        Calculate technical indicators for a given ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with keys: rsi, macd, macd_signal, bb_upper, bb_lower,
            sma_50, sma_200, current_price
        """
        try:
            # Fetch 1 year of daily data
            df = self.market.fetch_historical_data(ticker, period='1y', interval='1d')
            
            if df is None or len(df) < 20:
                # Not enough data - return safe defaults
                return {
                    'rsi': 50.0,
                    'macd': 0.0,
                    'macd_signal': 0.0,
                    'bb_upper': 0.0,
                    'bb_lower': 0.0,
                    'sma_50': 0.0,
                    'sma_200': 0.0,
                    'current_price': 0.0,
                }
            
            # Get closing prices
            close = df['Close']
            current_price = float(close.iloc[-1])
            
            # RSI (14-period)
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=14, min_periods=1).mean()
            avg_loss = loss.rolling(window=14, min_periods=1).mean()
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            rsi_value = float(rsi.iloc[-1]) if len(rsi) > 0 else 50.0
            
            # MACD (12, 26, 9)
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            macd_value = float(macd.iloc[-1]) if len(macd) > 0 else 0.0
            macd_signal_value = float(macd_signal.iloc[-1]) if len(macd_signal) > 0 else 0.0
            
            # Bollinger Bands (20-period, 2 std dev)
            sma20 = close.rolling(window=20, min_periods=1).mean()
            std20 = close.rolling(window=20, min_periods=1).std()
            bb_upper = sma20 + (2 * std20)
            bb_lower = sma20 - (2 * std20)
            bb_upper_value = float(bb_upper.iloc[-1]) if len(bb_upper) > 0 else current_price * 1.05
            bb_lower_value = float(bb_lower.iloc[-1]) if len(bb_lower) > 0 else current_price * 0.95
            
            # SMAs
            sma_50 = close.rolling(window=50, min_periods=1).mean()
            sma_200 = close.rolling(window=200, min_periods=1).mean()
            sma_50_value = float(sma_50.iloc[-1]) if len(sma_50) > 0 else current_price
            sma_200_value = float(sma_200.iloc[-1]) if len(sma_200) > 0 else current_price
            
            return {
                'rsi': rsi_value,
                'macd': macd_value,
                'macd_signal': macd_signal_value,
                'bb_upper': bb_upper_value,
                'bb_lower': bb_lower_value,
                'sma_50': sma_50_value,
                'sma_200': sma_200_value,
                'current_price': current_price,
            }
        
        except Exception as e:
            # On error, return safe defaults
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'bb_upper': 0.0,
                'bb_lower': 0.0,
                'sma_50': 0.0,
                'sma_200': 0.0,
                'current_price': 0.0,
            }

    def generate_signals(self, indicators: dict) -> dict:
        """
        Generate trading signals from technical indicators.

        Args:
            indicators: Dictionary with technical indicators

        Returns:
            Dictionary with signal labels for rsi and macd
        """
        signals = {}
        
        # RSI signals
        rsi = indicators.get('rsi', 50.0)
        if rsi > 70:
            signals['rsi'] = 'OVERBOUGHT'
        elif rsi < 30:
            signals['rsi'] = 'OVERSOLD'
        else:
            signals['rsi'] = 'NEUTRAL'
        
        # MACD signals
        macd = indicators.get('macd', 0.0)
        macd_signal = indicators.get('macd_signal', 0.0)
        if macd > macd_signal:
            signals['macd'] = 'BULLISH'
        elif macd < macd_signal:
            signals['macd'] = 'BEARISH'
        else:
            signals['macd'] = 'NEUTRAL'
        
        return signals

    def scan_macd_golden_crosses(self, tickers: list[str]) -> list[dict]:
        """Find tickers with a current or approaching daily MACD golden cross."""
        def scan_ticker(ticker: str) -> dict | None:
            try:
                history = self.market.fetch_historical_data(ticker, period="6mo", interval="1d")
                if history is None or len(history) < 35 or "Close" not in history:
                    return None

                close = history["Close"].dropna()
                macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
                signal = macd.ewm(span=9, adjust=False).mean()
                histogram = macd - signal
                status = self._classify_macd_cross(histogram)
                if status is None:
                    return None

                current_price = float(close.iloc[-1])
                info = self.market.fetch_ticker_info(ticker)
                name = info.get("longName") or info.get("shortName") or ticker

                return {
                    "Ticker": ticker,
                    "Name": name,
                    "Status": status,
                    "Current Price": current_price,
                    "Predicted Price (5d)": None,
                    "Expected Change (%)": None,
                }
            except Exception:
                return None

        results = []
        max_workers = min(getattr(self.market, "max_workers", 10), max(len(tickers), 1))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(scan_ticker, ticker) for ticker in dict.fromkeys(tickers)]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)

        status_order = {"Golden Cross": 0, "Approaching": 1}
        return sorted(results, key=lambda row: (status_order[row["Status"]], row["Ticker"]))

    @staticmethod
    def _classify_macd_cross(histogram: pd.Series) -> str | None:
        """Classify the latest MACD histogram as crossed, approaching, or neither."""
        recent = histogram.dropna().iloc[-5:]
        if len(recent) < 3:
            return None

        if recent.iloc[-2] <= 0 < recent.iloc[-1]:
            return "Golden Cross"

        latest_three = recent.iloc[-3:]
        gap_is_closing = latest_three.iloc[0] < latest_three.iloc[1] < latest_three.iloc[2] < 0
        recent_scale = max(float(recent.abs().max()), 1e-10)
        is_near_signal = abs(float(latest_three.iloc[-1])) <= recent_scale * 0.35
        if gap_is_closing and is_near_signal:
            return "Approaching"

        return None
