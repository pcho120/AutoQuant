from unittest.mock import Mock

from components import ticker_search


def test_search_tickers_finds_tusk_from_yahoo(monkeypatch):
    search_result = Mock()
    search_result.quotes = [
        {
            "symbol": "TUSK",
            "shortname": "Mammoth Energy Services, Inc.",
            "quoteType": "EQUITY",
        },
        {
            "symbol": "TUSK270219C00007500",
            "shortname": "TUSK call option",
            "quoteType": "OPTION",
        },
    ]
    monkeypatch.setattr(ticker_search.yf, "Search", lambda *args, **kwargs: search_result)
    ticker_search.search_yahoo_tickers.clear()

    results = ticker_search.search_tickers("tusk")

    assert results == [("TUSK - Mammoth Energy Services, Inc.", "TUSK")]


def test_search_tickers_uses_local_fallback_when_yahoo_fails(monkeypatch):
    def fail_search(*args, **kwargs):
        raise ConnectionError("offline")

    monkeypatch.setattr(ticker_search.yf, "Search", fail_search)
    ticker_search.search_yahoo_tickers.clear()

    assert ("AAPL", "AAPL") in ticker_search.search_tickers("aap")