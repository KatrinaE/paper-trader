import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from unittest.mock import patch, MagicMock
from rich.console import Console, ConsoleOptions, Group
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table, _Cell
from rich.prompt import Prompt
import requests

from main import get_market_data, create_layout, INSTRUMENTS

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")

def test_get_market_data():
    """Test fetching market data"""
    mock_response = {
        "EUR/USD_bid": {"bid": "1.1000"},
        "EUR/USD_ask": {"ask": "1.1005"},
        "GBP/USD_bid": {"bid": "1.2500"},
        "GBP/USD_ask": {"ask": "1.2505"},
        "XAU/USD_bid": {"bid": "1900.00"},
        "XAU/USD_ask": {"ask": "1900.50"},
        "AAPL_bid": {"bid": "180.00"},
        "AAPL_ask": {"ask": "180.05"}
    }

    with patch('requests.get') as mock_get:
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_get.return_value = mock_response_obj

        data = get_market_data()
        assert data is not None
        assert "EUR/USD_bid" in data
        assert "EUR/USD_ask" in data
        assert "GBP/USD_bid" in data
        assert "GBP/USD_ask" in data
        assert "AAPL_bid" in data
        assert "AAPL_ask" in data

def test_create_layout():
    """Test creating the layout with sample data"""
    sample_data = {
        "EUR/USD_bid": {"bid": "1.1000"},
        "EUR/USD_ask": {"ask": "1.1005"},
        "GBP/USD_bid": {"bid": "1.2500"},
        "GBP/USD_ask": {"ask": "1.2505"},
        "XAU/USD_bid": {"bid": "1900.00"},
        "XAU/USD_ask": {"ask": "1900.50"},
        "AAPL_bid": {"bid": "180.00"},
        "AAPL_ask": {"ask": "180.05"}
    }

    layout = create_layout(sample_data)
    assert layout is not None

    # Verify layout structure
    assert isinstance(layout, Group)
    assert len(layout.renderables) == 2  # Should have 2 rows

    # Verify first row (Forex and Commodities)
    top_row = layout.renderables[0]
    assert isinstance(top_row, Columns)
    assert len(top_row.renderables) == 2  # Should have 2 columns

    # Verify second row (Stocks and Controls)
    bottom_row = layout.renderables[1]
    assert isinstance(bottom_row, Columns)
    assert len(bottom_row.renderables) == 2  # Should have 2 columns

    # Verify panel titles and styles
    forex_panel = top_row.renderables[0]
    commodities_panel = top_row.renderables[1]
    stocks_panel = bottom_row.renderables[0]
    controls_panel = bottom_row.renderables[1]

    assert forex_panel.title == "Forex"
    assert commodities_panel.title == "Commodities"
    assert stocks_panel.title == "Stocks"
    assert controls_panel.title == "Controls"

    assert forex_panel.border_style == "cyan"
    assert commodities_panel.border_style == "yellow"
    assert stocks_panel.border_style == "magenta"
    assert controls_panel.border_style == "green"

    # Verify table structure
    forex_table = forex_panel.renderable
    assert isinstance(forex_table, Table)
    assert len(forex_table.columns) == 3  # Instrument, Bid, Ask columns
    assert forex_table.columns[0].header == "Instrument"
    assert forex_table.columns[1].header == "Bid"
    assert forex_table.columns[2].header == "Ask"

    # Test adding an instrument
    with patch('rich.prompt.Prompt.ask', side_effect=['GBP/USD', 'forex']):
        mock_live = MagicMock()
        # Mock the INSTRUMENTS list to include our new instrument
        with patch('main.INSTRUMENTS', [
            {'symbol': 'EUR/USD', 'category': 'forex'},
            {'symbol': 'GBP/USD', 'category': 'forex'}
        ]):
            layout = create_layout(sample_data)
            assert layout is not None

            # Verify the new instrument was added
            forex_table = layout.renderables[0].renderables[0].renderable
            # Verify EUR/USD row exists and has correct data
            found_eur = False
            found_gbp = False

            # Verify number of rows
            assert len(forex_table.rows) == 2

            # Verify table rows
            assert len(forex_table.rows) == 2

            # Create a console to render the table
            console = Console()

            # Verify EUR/USD row
            with console.capture() as capture:
                console.print(forex_table)
            output = capture.get()
            if "EUR/USD" in output and "1.1000" in output and "1.1005" in output:
                found_eur = True
            if "GBP/USD" in output and "1.2500" in output and "1.2505" in output:
                found_gbp = True

            assert found_eur, "EUR/USD row not found"
            assert found_gbp, "GBP/USD row not found"

def test_add_remove_instrument():
    """Test adding and removing instruments"""
    sample_data = {
        "EUR/USD_bid": {"bid": "1.1000"},
        "EUR/USD_ask": {"ask": "1.1005"}
    }

    # Test adding instrument
    with patch('rich.prompt.Prompt.ask', side_effect=['GBP/USD', 'forex']):
        mock_live = MagicMock()
        layout = create_layout(sample_data)
        assert layout is not None

    # Test removing instrument
    with patch('rich.prompt.Prompt.ask', side_effect=['EUR/USD']):
        mock_live = MagicMock()
        layout = create_layout(sample_data)
        assert layout is not None

if __name__ == '__main__':
    test_get_market_data()
    test_create_layout()
    test_add_remove_instrument()
    print("All tests passed!")
