import unittest
from unittest.mock import patch, MagicMock

from exchange import Exchange
from products import PRODUCTS
from trading import Order, Fill
from trading_book import TradingBook
from user_actions import BUY, SELL, _add_product, _remove_product, _trade_product

class TestAddProduct(unittest.TestCase):
    def test_add_forex(self):
        """
        Test adding a new forex product
        """
        products_fixture = PRODUCTS.copy()
        new_product = {
            "symbol": "NZD/USD",
            "name": "New Zealand Dollar - US Dollar exchange rate",
            "category": "forex"
        }
        products_fixture.append(new_product)
        _add_product(new_product["symbol"], new_product["name"], new_product["category"])
        self.assertEqual(PRODUCTS, products_fixture)

class TestRemoveProduct(unittest.TestCase):
    def test_remove_forex(self):
        """
        Test removing a forex product.
        """
        products_fixture = PRODUCTS.copy()
        products_fixture.remove({"symbol": "EUR/USD", "name": "Euro - US Dollar exchange rate", "category": "forex"})
        symbol = "EUR/USD"
        _remove_product(symbol)
        self.assertEqual(PRODUCTS, products_fixture)

class TestTradeProduct(unittest.TestCase):
    def test_buy_forex(self):
        market_data_source = 'none'
        trading_book = TradingBook()
        exchange = Exchange({})
        product = 'AAPL'
        quantity = 5
        side = BUY
        verbosity = 1

        trading_book_fixture = TradingBook()

        # Do not check fill price because it's set nondeterministically by market data
        fill_fixture = Fill(product, quantity, side, None)

        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, side, verbosity)

        self.assertEqual(trading_book.cash, trading_book_fixture.cash - fill.quantity * fill.price)
        self.assertEqual(trading_book.positions, {product: quantity})

        self.assertEqual(fill.side, fill_fixture.side)
        self.assertEqual(fill.product, fill_fixture.product)
        self.assertEqual(fill.quantity, fill_fixture.quantity)
        self.assertNotEqual(fill.price, None)

    def test_sell_forex(self):
        market_data_source = 'none'
        product = "AAPL"
        quantity_fixture = 5
        trading_book = TradingBook()
        trading_book.positions = {product: quantity_fixture}
        exchange = Exchange({})
        quantity = 3
        side = SELL
        verbosity = 1

        trading_book_fixture = TradingBook()

        # Do not check fill price because it's set nondeterministically by market data
        fill_fixture = Fill(product, quantity, side, None)

        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, side, verbosity)

        self.assertEqual(trading_book.cash, trading_book_fixture.cash + fill.quantity * fill.price)
        self.assertEqual(trading_book.positions, {product: quantity_fixture - quantity})

        self.assertEqual(fill.side, fill_fixture.side)
        self.assertEqual(fill.product, fill_fixture.product)
        self.assertEqual(fill.quantity, fill_fixture.quantity)
        self.assertNotEqual(fill.price, None)

if __name__ == '__main__':
    unittest.main()
