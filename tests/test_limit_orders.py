import logging
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from trading import Order, OrderBook
from trading_book import TradingBook

class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.order_book = OrderBook()
        self.market_data = {
            "AAPL_bid": 150.0,
            "AAPL_ask": 150.5,
            "GOOGL_bid": 2800.0,
            "GOOGL_ask": 2805.0
        }

    def test_place_market_order(self):
        """Test placing and matching a market order"""
        order_id = self.order_book.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.MARKET
        )

        # Process market data to match orders
        matches = self.order_book.match_orders(self.market_data)

        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 150.5)  # Should match ask price

    def test_place_limit_order(self):
        """Test placing a limit order that matches immediately"""
        order_id = self.order_book.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=151.0  # Above current ask price
        )

        matches = self.order_book.match_orders(self.market_data)

        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 150.5)  # Should match at market price

    def test_limit_order_no_match(self):
        """Test placing a limit order that doesn't match immediately"""
        order_id = self.order_book.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0  # Below current ask price
        )

        matches = self.order_book.match_orders(self.market_data)

        self.assertEqual(len(matches), 0)  # No match since limit price not met
        active_orders = self.order_book.get_active_orders()
        self.assertIn(order_id, active_orders)

    def test_limit_order_match_later(self):
        """Test placing a limit order that matches later when price improves"""
        order_id = self.order_book.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0  # Below current ask price
        )

        # First market data update - no match
        matches = self.order_book.match_orders(self.market_data)
        self.assertEqual(len(matches), 0)

        # Update market data with better price
        self.market_data["AAPL_ask"] = 149.0
        matches = self.order_book.match_orders(self.market_data)

        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 149.0)  # Should match at new ask price

    def test_cancel_order(self):
        """Test cancelling an order"""
        order_id = self.order_book.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0
        )

        # Cancel the order
        success = self.order_book.cancel_order(order_id)
        self.assertTrue(success)

        # Process market data - order should not match
        matches = self.order_book.match_orders(self.market_data)
        self.assertEqual(len(matches), 0)

        # Order should not be in active orders
        active_orders = self.order_book.get_active_orders()
        self.assertNotIn(order_id, active_orders)

    def test_order_book_sorting(self):
        """Test that order book maintains correct sorting"""
        # Place multiple buy orders with different prices
        self.order_book.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 150.0)
        self.order_book.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 155.0)
        self.order_book.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 145.0)

        # Orders should be sorted by price (highest first) then timestamp
        buy_orders = self.order_book.buy_orders["AAPL"]
        self.assertEqual(len(buy_orders), 3)
        self.assertEqual(buy_orders[0].limit_price, 155.0)  # Highest price first
        self.assertEqual(buy_orders[1].limit_price, 150.0)
        self.assertEqual(buy_orders[2].limit_price, 145.0)  # Lowest price last

    def test_partially_filled_order(self):
        """Test an order that gets partially filled"""
        # Place a large order
        order_id = self.order_book.place_order(
            "AAPL",
            200,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=150.0
        )

        # Update market data with smaller quantity available
        self.market_data["AAPL_ask"] = 150.0
        self.market_data["AAPL_bid"] = 149.5

        # Process market data - should fill partially
        matches = self.order_book.match_orders(self.market_data)
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(fill.quantity, 100)  # Only half filled
        self.assertEqual(order.remaining_quantity(), 100)  # 100 still remaining

        # Process again with same price - should fill remaining
        matches = self.order_book.match_orders(self.market_data)
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(fill.quantity, 100)  # Remaining half filled
        self.assertEqual(order.remaining_quantity(), 0)  # Fully filled

if __name__ == '__main__':
    unittest.main()
