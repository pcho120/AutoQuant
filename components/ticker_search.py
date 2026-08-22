import streamlit as st
import yfinance as yf
from streamlit_searchbox import st_searchbox


SUPPORTED_QUOTE_TYPES = {
    "CRYPTOCURRENCY",
    "CURRENCY",
    "EQUITY",
    "ETF",
    "FUTURE",
    "INDEX",
    "MUTUALFUND",
}


@st.cache_data(ttl=3600)
def get_ticker_list() -> list[str]:
    """
    Cached ticker source with 1-hour TTL.
    
    Returns:
        List of common stock ticker symbols
    """
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JNJ", "V",
        "WMT", "JPM", "MA", "PG", "DIS", "ADBE", "CRM", "NFLX", "PYPL", "INTC",
        "AMD", "MU", "QUALCOMM", "IBM", "CSCO", "ORCL", "SAP", "VMware", "TXN", "STM",
        "GOOG", "FB", "AMZN", "BABA", "TCEHY", "JD", "BIDU", "NTES", "NETEASE", "RXO",
        "SPY", "QQQ", "IVV", "VOO", "VTI", "BND", "AGG", "GLD", "TLT", "LQD",
        "F", "GM", "TM", "HMC", "TSM", "ASX", "SSNLF", "UNH", "CVS", "ABT",
        "PFE", "MRK", "GILD", "BIIB", "REGN", "VEEV", "ILMN", "CRSP", "EDIT", "BEAM",
        "XOM", "CVX", "COP", "EOG", "PSX", "MPC", "VLO", "HES", "OKE", "EQT",
        "BAC", "WFC", "GS", "BLK", "SCHW", "CME", "ICE", "CBOE", "MSCI", "SPGI",
        "SO", "NEE", "DUK", "EXC", "AEP", "XEL", "D", "PPL", "ETR", "ED",
        "PLD", "AMT", "CCI", "EQIX", "DLR", "VICI", "SBAC", "CONE", "STAG", "PEG"
    ]


@st.cache_data(ttl=3600, show_spinner=False)
def search_yahoo_tickers(query: str) -> list[tuple[str, str]]:
    """Search Yahoo Finance for ticker symbols and display names."""
    try:
        quotes = yf.Search(query, max_results=15).quotes
    except Exception:
        return []

    results = []
    seen = set()
    for quote in quotes:
        symbol = quote.get("symbol", "").upper()
        quote_type = quote.get("quoteType", "").upper()
        if not symbol or symbol in seen or quote_type not in SUPPORTED_QUOTE_TYPES:
            continue

        name = quote.get("shortname") or quote.get("longname")
        label = f"{symbol} - {name}" if name else symbol
        results.append((label, symbol))
        seen.add(symbol)

    return results


def search_tickers(query: str) -> list[tuple[str, str]]:
    """
    Search Yahoo Finance, with common ticker symbols as an offline fallback.
    
    Args:
        query: Search query string (empty returns empty list)
    
    Returns:
        List of (label, value) tuples, max 15 results
    """
    if not query:
        return []
    
    query_upper = query.strip().upper()
    live_results = search_yahoo_tickers(query_upper)
    seen = {value for _, value in live_results}
    fallback_results = [
        (ticker, ticker)
        for ticker in get_ticker_list()
        if ticker.startswith(query_upper) and ticker not in seen
    ]

    return (live_results + fallback_results)[:15]


def render_ticker_search(key: str, placeholder: str = "Search ticker...") -> str:
    """
    Render a searchable ticker input using st_searchbox component.
    
    Args:
        key: Unique Streamlit session state key
        placeholder: Placeholder text for search input
    
    Returns:
        Selected ticker symbol string (empty if no selection)
    """
    selected = st_searchbox(
        search_function=search_tickers,
        placeholder=placeholder,
        key=key
    )
    
    return selected if selected else ""
