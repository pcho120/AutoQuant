import streamlit as st
from streamlit_searchbox import st_searchbox


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


def search_tickers(query: str) -> list[tuple[str, str]]:
    """
    Search tickers by prefix matching (case-insensitive).
    
    Args:
        query: Search query string (empty returns empty list)
    
    Returns:
        List of (label, value) tuples, max 15 results
    """
    if not query:
        return []
    
    query_upper = query.upper()
    tickers = get_ticker_list()
    matches = [t for t in tickers if t.startswith(query_upper)]
    
    return [(ticker, ticker) for ticker in matches[:15]]


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
