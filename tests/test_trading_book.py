import unittest
from unittest.mock import MagicMock

from trading_book import TradingBook
from order import Fill
from market_data import get_market_data
from products import PRODUCTS

class TestTradingBook(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.trading_book = TradingBook()
        self.market_data = get_market_data('none')  # Get random market data

    def test_buy_and_display(self):
        """Test buying a product and verify it displays correctly in the trading book"""
        # Mock the buy action
        product = "AAPL"
        quantity = 5
        price = self.market_data.get("AAPL_bid", 100.0)

        # Simulate a buy (add to position)
        self.trading_book.cash -= quantity * price
        self.trading_book.add_to_position(product, quantity)

        # Verify position is displayed correctly
        positions = self.trading_book.positions
        self.assertIn(product, positions)
        self.assertEqual(positions[product], quantity)

        # Verify value calculation
        total_value = self.trading_book.get_total_value(self.market_data)
        expected_value = self.trading_book.cash + (quantity * price)
        self.assertEqual(total_value, expected_value)

    def test_sell_and_display(self):
        """Test selling a product and verify it displays correctly in the trading book"""
        # First buy some shares
        product = "AAPL"
        quantity = 5
        price = self.market_data.get("AAPL_bid", 100.0)

        # Add initial position
        self.trading_book.add_to_position(product, quantity)

        # Now sell
        sell_quantity = 2
        self.trading_book.cash += sell_quantity * price
        self.trading_book.remove_from_position(product, sell_quantity)

        # Verify position is updated correctly
        remaining_quantity = quantity - sell_quantity
        self.assertEqual(self.trading_book.positions[product], remaining_quantity)

        # Verify value calculation
        total_value = self.trading_book.get_total_value(self.market_data)
        expected_value = self.trading_book.cash + (remaining_quantity * price)
        self.assertEqual(total_value, expected_value)

    def test_position_value_updates(self):
        """Test that position values update correctly with changing market prices"""
        # Buy some shares
        product = "AAPL"
        quantity = 5
        initial_price = self.market_data.get("AAPL_bid", 100.0)

        # Add initial position
        self.trading_book.cash -= quantity * initial_price
        self.trading_book.add_to_position(product, quantity)

        # Get new market data with different prices
        new_market_data = get_market_data('none')
        new_price = new_market_data.get("AAPL_bid", 100.0)

        # Verify position value updates with new price
        total_value = self.trading_book.get_total_value(new_market_data)
        expected_value = self.trading_book.cash + (quantity * new_price)
        self.assertEqual(total_value, expected_value)

if __name__ == '__main__':
    unittest.main()
