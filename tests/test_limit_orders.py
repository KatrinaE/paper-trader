import logging
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from trading import Order
from exchange import Exchange
from trading_book import TradingBook

logger = logging.getLogger(__name__)

class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.market_data = {
            "AAPL_bid": 150.0,
            "AAPL_ask": 150.5,
            "GOOGL_bid": 2800.0,
            "GOOGL_ask": 2805.0
        }
        self.exchange = Exchange(self.market_data)

    def test_place_market_order(self):
        """Test placing and matching a market order"""
        order_id = self.exchange.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.MARKET
        )

        # Process market data to match orders
        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 150.5)

    def test_place_limit_order(self):
        """Test placing a limit order that matches immediately"""
        order_id = self.exchange.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=151.0  # Above current ask price
        )

        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 150.5)

    def test_limit_order_no_match(self):
        """Test placing a limit order that doesn't match immediately"""
        order_id = self.exchange.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0  # Below current ask price
        )

        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 0)

    def test_limit_order_match_later(self):
        """Test placing a limit order that matches later when price improves"""
        order_id = self.exchange.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0  # Below current ask price
        )

        # First market data update - no match
        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 0)

        # Update market data to improve price
        self.market_data["AAPL_ask"] = 149.0
        self.exchange.update_market_data(self.market_data)
        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)
        self.assertEqual(fill.price, 149.0)

    def test_partially_filled_order(self):
        """Test an order that gets partially filled"""
        # Place a large order
        order_id = self.exchange.place_order(
            "AAPL",
            200,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=150.0
        )

        # Update market data with smaller quantity available
        self.market_data["AAPL_ask"] = 150.0
        self.market_data["AAPL_bid"] = 149.5
        self.exchange.update_market_data(self.market_data)
        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 1)
        order, fill = matches[0]
        self.assertEqual(order.order_id, order_id)
        self.assertEqual(fill.quantity, 100)  # MAX_FILL_QUANTITY is 100
        self.assertEqual(fill.price, 150.0)

    def test_cancel_order(self):
        """Test cancelling an order"""
        order_id = self.exchange.place_order(
            "AAPL",
            100,
            Order.OrderSide.BUY,
            Order.OrderType.LIMIT,
            limit_price=149.0
        )

        # Cancel the order
        success = self.exchange.cancel_order(order_id)
        self.assertTrue(success)

        # Process market data - order should not match
        matches = self.exchange.match_orders()
        self.assertEqual(len(matches), 0)

    def test_order_book_sorting(self):
        """Test that orders are sorted correctly in the order book"""
        # Place multiple limit orders
        self.exchange.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 150.0)
        self.exchange.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 155.0)
        self.exchange.place_order("AAPL", 100, Order.OrderSide.BUY, Order.OrderType.LIMIT, 145.0)

        # Verify buy orders are sorted by price (highest first)
        buy_orders = self.exchange.buy_orders["AAPL"]
        self.assertEqual(len(buy_orders), 3)
        self.assertEqual(buy_orders[0].limit_price, 155.0)
        self.assertEqual(buy_orders[1].limit_price, 150.0)
        self.assertEqual(buy_orders[2].limit_price, 145.0)

        # Place sell orders
        self.exchange.place_order("AAPL", 100, Order.OrderSide.SELL, Order.OrderType.LIMIT, 150.0)
        self.exchange.place_order("AAPL", 100, Order.OrderSide.SELL, Order.OrderType.LIMIT, 155.0)
        self.exchange.place_order("AAPL", 100, Order.OrderSide.SELL, Order.OrderType.LIMIT, 145.0)

        # Verify sell orders are sorted by price (lowest first)
        sell_orders = self.exchange.sell_orders["AAPL"]
        self.assertEqual(len(sell_orders), 3)
        self.assertEqual(sell_orders[0].limit_price, 145.0)
        self.assertEqual(sell_orders[1].limit_price, 150.0)
        self.assertEqual(sell_orders[2].limit_price, 155.0)

if __name__ == '__main__':
    unittest.main()
