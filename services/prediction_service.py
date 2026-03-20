from domain.prediction import PredictionRequest, PredictionResult
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
        """
        Predict stock price for a given ticker and horizon.

        Args:
            request: PredictionRequest with ticker, horizon, and optional flags

        Returns:
            PredictionResult with predicted price and confidence score
        """
        # Fetch current price via market adapter
        prices = self.market.fetch_current_prices([request.ticker])
        current_price = prices.get(request.ticker, 0.0)

        # Initialize score components
        score = 0.0
        reasoning_parts = []

        # 30% news sentiment contribution
        if request.include_news:
            news_articles = self.news.fetch_news(request.ticker)
            if news_articles:
                sentiment_sum = sum(self.news.get_sentiment(article) for article in news_articles)
                news_sentiment = sentiment_sum / len(news_articles)
                score += news_sentiment * 0.30
                reasoning_parts.append(f"News sentiment: {news_sentiment:.2f}")
            else:
                reasoning_parts.append("No recent news")
        else:
            reasoning_parts.append("News not included")

        # 70% indicator contribution (RSI 20%, MACD 30%, MA 20%)
        if request.include_indicators:
            indicators = self.calculate_indicators(request.ticker)
            signals = self.generate_signals(indicators)

            # RSI contribution (20%)
            rsi = indicators.get('rsi', 50.0)
            rsi_score = (rsi - 50.0) / 50.0  # Convert to [-1, 1]
            score += rsi_score * 0.20

            # MACD contribution (30%)
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_diff = macd - macd_signal
            max_price = indicators.get('current_price', 1.0)
            if max_price > 0:
                macd_score = max(-1.0, min(1.0, macd_diff / max_price))
            else:
                macd_score = 0.0
            score += macd_score * 0.30

            # MA contribution (20%)
            sma_50 = indicators.get('sma_50', current_price)
            sma_200 = indicators.get('sma_200', current_price)
            ma_current = current_price
            if sma_50 > 0 and sma_200 > 0:
                ma_score = ((ma_current - sma_200) / sma_200) * 0.5
                ma_score = max(-1.0, min(1.0, ma_score))
            else:
                ma_score = 0.0
            score += ma_score * 0.20

            reasoning_parts.append(f"RSI: {signals.get('rsi', 'N/A')}, MACD: {signals.get('macd', 'N/A')}")
        else:
            reasoning_parts.append("Indicators not included")

        # Clamp score to [-1, 1]
        score = max(-1.0, min(1.0, score))

        # Calculate predicted price with max_change of 20%
        max_change = 0.20
        predicted_price = current_price * (1 + score * max_change)

        # Calculate confidence: min(abs(score) * 100, 85) bounded [0, 100]
        confidence = min(abs(score) * 100, 85)
        confidence = max(0.0, min(100.0, confidence))

        # Create result
        return PredictionResult(
            ticker=request.ticker,
            current_price=current_price,
            predicted_price=predicted_price,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            chart_data=None,
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
