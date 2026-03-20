import requests
from typing import List, Dict
from datetime import datetime, timedelta


class NewsProvider:
    """
    Adapter for fetching news and sentiment data from NewsAPI.
    
    Provides news articles for stock tickers and keyword-based sentiment analysis.
    Handles API failures gracefully by returning empty results.
    """

    def __init__(self, api_key: str):
        """
        Initialize the news provider with an API key.

        Args:
            api_key: API key for NewsAPI service
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"

    def fetch_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Fetch recent news articles for a given ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            days: Number of days to look back (default: 7)

        Returns:
            List of news article dictionaries with metadata.
            Returns empty list on API failures or invalid responses.
        """
        if not self.api_key or self.api_key in ("DEMO_KEY", "test-key", "test"):
            return []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            params = {
                "q": ticker,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "apiKey": self.api_key,
                "language": "en",
                "sortBy": "relevancy"
            }
            
            response = requests.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok" and isinstance(data.get("articles"), list):
                    return data.get("articles", [])
            
            return []
        except Exception:
            return []

    def get_sentiment(self, article: dict) -> float:
        """
        Analyze sentiment of a news article using keyword-based heuristic.

        Args:
            article: News article dictionary with 'title' and 'description' fields

        Returns:
            Sentiment score as float bounded to [-1.0, 1.0].
            Returns 0.0 if no sentiment keywords found.
        """
        positive_keywords = [
            "profit", "growth", "bullish", "upgrade", "beat",
            "surge", "gains", "strong", "outperform", "rally"
        ]
        negative_keywords = [
            "loss", "decline", "bearish", "downgrade", "miss",
            "plunge", "weak", "underperform", "sell", "crash"
        ]
        
        text = (
            article.get("title", "") + " " + 
            article.get("description", "")
        ).lower()
        
        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)
        
        if pos_count + neg_count == 0:
            return 0.0
        
        raw_sentiment = (pos_count - neg_count) / (pos_count + neg_count)
        
        return max(-1.0, min(1.0, raw_sentiment))
