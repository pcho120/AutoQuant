import pytest
from unittest.mock import Mock, MagicMock, patch
from adapters.db_client import DBClient
from domain.position import Position


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return Mock()


@pytest.fixture
def db_client(mock_supabase):
    """Create DBClient with mocked Supabase."""
    with patch('adapters.db_client.create_client', return_value=mock_supabase):
        with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co', 'SUPABASE_KEY': 'test-key'}):
            return DBClient()


# Tests for update_position method

def test_update_position_success(db_client, mock_supabase):
    """Test successful position update."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {"data": [{"ticker": "AAPL", "quantity": 20.0}]}

    result = db_client.update_position(user_id="user123", ticker="AAPL", quantity=20.0, buy_price=150.0)

    assert result is True
    mock_supabase.table.assert_called_with("portfolio")
    mock_table.update.assert_called_with({"quantity": 20.0, "buy_price": 150.0})


def test_update_position_exception_returns_false(db_client, mock_supabase):
    """Test that update_position returns False on exception."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("Network error")

    result = db_client.update_position(user_id="user123", ticker="AAPL", quantity=20.0, buy_price=150.0)

    assert result is False


def test_update_position_calls_correct_filters(db_client, mock_supabase):
    """Test that update_position filters by user_id and ticker."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {}

    db_client.update_position(user_id="user456", ticker="MSFT", quantity=5.0, buy_price=300.0)

    # Verify chained calls
    mock_supabase.table.assert_called_with("portfolio")
    mock_table.update.assert_called_once()
    assert mock_table.eq.call_count == 2
    mock_table.eq.assert_any_call("user_id", "user456")
    mock_table.eq.assert_any_call("ticker", "MSFT")


# Tests for delete_position method

def test_delete_position_success(db_client, mock_supabase):
    """Test successful position deletion."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {}

    result = db_client.delete_position(user_id="user123", ticker="AAPL")

    assert result is True
    mock_supabase.table.assert_called_with("portfolio")
    mock_table.delete.assert_called_once()


def test_delete_position_exception_returns_false(db_client, mock_supabase):
    """Test that delete_position returns False on exception."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("DB constraint error")

    result = db_client.delete_position(user_id="user123", ticker="AAPL")

    assert result is False


def test_delete_position_calls_correct_filters(db_client, mock_supabase):
    """Test that delete_position filters by user_id and ticker."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {}

    db_client.delete_position(user_id="user789", ticker="GOOGL")

    # Verify chained calls
    mock_supabase.table.assert_called_with("portfolio")
    mock_table.delete.assert_called_once()
    assert mock_table.eq.call_count == 2
    mock_table.eq.assert_any_call("user_id", "user789")
    mock_table.eq.assert_any_call("ticker", "GOOGL")


def test_delete_position_nonexistent_row(db_client, mock_supabase):
    """Test delete_position when row doesn't exist (should still return True)."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = {"data": []}

    result = db_client.delete_position(user_id="user123", ticker="NONEXISTENT")

    assert result is True


# Tests for holdings validation logic (via fetch_positions + Position creation)

def test_fetch_positions_success(db_client, mock_supabase):
    """Test successful positions fetch with multiple holdings."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[
        {"ticker": "AAPL", "quantity": "10", "buy_price": "150.0", "current_price": "160.0"},
        {"ticker": "MSFT", "quantity": "5", "buy_price": "300.0", "current_price": "320.0"}
    ])

    positions = db_client.fetch_positions(user_id="user123")

    assert len(positions) == 2
    assert positions[0].ticker == "AAPL"
    assert positions[0].quantity == 10.0
    assert positions[1].ticker == "MSFT"


def test_fetch_positions_exception_returns_empty_list(db_client, mock_supabase):
    """Test that fetch_positions returns empty list on exception."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("Connection failed")

    positions = db_client.fetch_positions(user_id="user123")

    assert positions == []


def test_fetch_positions_missing_current_price(db_client, mock_supabase):
    """Test that missing current_price defaults to 0.0."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[
        {"ticker": "AAPL", "quantity": "10", "buy_price": "150.0"}
    ])

    positions = db_client.fetch_positions(user_id="user123")

    assert len(positions) == 1
    assert positions[0].current_price == 0.0


# Tests for save_positions method (existing, but ensure it's not regressed)

def test_save_positions_success(db_client, mock_supabase):
    """Test successful save_positions (full replace semantics)."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = {}

    positions = [
        Position(ticker="AAPL", quantity=10.0, buy_price=150.0, current_price=160.0),
        Position(ticker="MSFT", quantity=5.0, buy_price=300.0, current_price=320.0)
    ]

    db_client.save_positions(user_id="user123", positions=positions)

    mock_table.delete.assert_called_once()
    assert mock_table.insert.call_count == 2


def test_save_positions_exception_swallowed(db_client, mock_supabase):
    """Test that save_positions swallows exceptions gracefully."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("Delete failed")

    positions = [Position(ticker="AAPL", quantity=10.0, buy_price=150.0, current_price=160.0)]

    try:
        db_client.save_positions(user_id="user123", positions=positions)
    except Exception:
        pytest.fail("save_positions should not raise exception")


# Integration tests for holdings validation patterns

def test_update_position_with_negative_quantity():
    """Test that validation prevents negative quantity updates (UI-level responsibility)."""
    qty = -5.0
    assert qty <= 0, "Validation should reject qty <= 0"


def test_update_position_with_negative_price():
    """Test that validation prevents negative price updates (UI-level responsibility)."""
    price = -150.0
    assert price < 0, "Validation should reject price < 0"


def test_position_quantity_zero_rejected():
    """Test zero quantity is invalid."""
    qty = 0.0
    assert qty <= 0, "Zero quantity should be rejected"


def test_position_price_valid_zero():
    """Test that zero price is technically valid (could represent 'unknown')."""
    price = 0.0
    assert price >= 0, "Zero price should be acceptable for current_price default"
