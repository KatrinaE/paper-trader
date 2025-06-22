import unittest
from unittest.mock import patch, MagicMock

from exchange import Exchange
from products import PRODUCTS, Product
from trading import Order, Fill, OrderBook
from trading_book import TradingBook
from user_actions import BUY, SELL, _add_product, _remove_product, _trade_product
# Removed market_data_config import since it's not needed anymore

class TestAddProduct(unittest.TestCase):
    def test_add_forex(self):
        """
        Test adding a new forex product
        """
        products_fixture = PRODUCTS.copy()
        new_product = Product(
            symbol="NZD/USD",
            name="New Zealand Dollar - US Dollar exchange rate",
            category="forex",
            initial_price=100.0  # Same as default in _add_product
        )
        products_fixture.append(new_product)
        _add_product(new_product.symbol, new_product.name, new_product.category)
        # Convert both lists to sets of tuples for comparison
        products_set = {(p.symbol, p.name, p.category, p.initial_price) for p in PRODUCTS}
        fixture_set = {(p.symbol, p.name, p.category, p.initial_price) for p in products_fixture}
        self.assertEqual(products_set, fixture_set)

class TestRemoveProduct(unittest.TestCase):
    def test_remove_forex(self):
        """
        Test removing a forex product.
        """
        products_fixture = PRODUCTS.copy()
        # Find the EUR/USD product in the list
        eurusd_product = next(p for p in products_fixture if p.symbol == 'EUR/USD')
        products_fixture.remove(eurusd_product)
        symbol = "EUR/USD"
        _remove_product(symbol)
        self.assertEqual(PRODUCTS, products_fixture)

class TestTradeProduct(unittest.TestCase):
    def test_buy_forex(self):
        market_data_source = 'none'
        trading_book = TradingBook()
        market_data = {
            "AAPL_ask": 150.0,
            "AAPL_bid": 149.5
        }
        exchange = Exchange(market_data)
        # Get a Product instance instead of using string symbol
        product = next(p for p in PRODUCTS if p.symbol == 'AAPL')
        quantity = 5
        order_book = OrderBook()
        order_id = order_book.place_order(
            product=product.symbol,
            quantity=quantity,
            side=Order.OrderSide.BUY,
            order_type=Order.OrderType.MARKET
        )
        order = order_book.orders[order_id]
        side = Order.OrderSide.BUY
        verbosity = 1

        # Set up market data
        market_data = {
            f"{product.symbol}_ask": 150.0,
            f"{product.symbol}_bid": 149.5
        }
        exchange.update_market_data(market_data)

        trading_book_fixture = TradingBook()

        # Do not check fill price because it's set nondeterministically by market data
        fill_fixture = Fill(product.symbol, quantity, side, None)

        fill = exchange.execute_order(order)
        trading_book.cash -= fill.quantity * fill.price
        trading_book.add_to_position(fill.product, fill.quantity)

        self.assertEqual(trading_book.cash, trading_book_fixture.cash - fill.quantity * fill.price)
        self.assertEqual(trading_book.positions, {product.symbol: quantity})

        self.assertEqual(fill.side, fill_fixture.side)
        self.assertEqual(fill.product, fill_fixture.product)
        self.assertEqual(fill.quantity, fill_fixture.quantity)
        self.assertNotEqual(fill.price, None)

    def test_sell_forex(self):
        market_data_source = 'none'
        # Get a Product instance instead of using string symbol
        product = next(p for p in PRODUCTS if p.symbol == 'AAPL')
        quantity_fixture = 5
        trading_book = TradingBook()
        trading_book.positions = {product.symbol: quantity_fixture}
        market_data = {
            "AAPL_ask": 150.0,
            "AAPL_bid": 149.5
        }
        exchange = Exchange(market_data)
        quantity = 3
        side = Order.OrderSide.SELL
        verbosity = 1

        # Set up market data
        market_data = {
            f"{product.symbol}_ask": 150.0,
            f"{product.symbol}_bid": 149.5
        }
        exchange.update_market_data(market_data)

        trading_book_fixture = TradingBook()

        # Do not check fill price because it's set nondeterministically by market data
        fill_fixture = Fill(product.symbol, quantity, side, None)

        order_book = OrderBook()
        order_id = order_book.place_order(
            product=product.symbol,
            quantity=quantity,
            side=Order.OrderSide.SELL,
            order_type=Order.OrderType.MARKET
        )
        order = order_book.orders[order_id]
        fill = exchange.execute_order(order)
        trading_book.cash += fill.quantity * fill.price
        trading_book.remove_from_position(fill.product, fill.quantity)

        self.assertEqual(trading_book.cash, trading_book_fixture.cash + fill.quantity * fill.price)
        self.assertEqual(trading_book.positions, {product.symbol: quantity_fixture - quantity})

        self.assertEqual(fill.side, fill_fixture.side)
        self.assertEqual(fill.product, fill_fixture.product)
        self.assertEqual(fill.quantity, fill_fixture.quantity)
        self.assertNotEqual(fill.price, None)

if __name__ == '__main__':
    unittest.main()
