import unittest
from unittest.mock import patch
from exchange import Exchange
from order import Order, Fill
from market_data import get_market_data, MarketDataSource, generate_simulated_order
from products import PRODUCTS, Product
from trading_book import TradingBook

class TestCLOBFunctionality(unittest.TestCase):
    def setUp(self):
        """Initialize test setup"""
        self.exchange = Exchange({})
        self.trading_book = TradingBook()
        self.trading_book.exchange = self.exchange
        
        # Test product
        self.test_product = PRODUCTS[0]  # Use first product (EUR/USD)

    def test_order_source_enum(self):
        """Test that OrderSource enum works correctly"""
        user_order = Order(
            order_id=1,
            product="EUR/USD",
            quantity=10,
            side=Order.OrderSide.BUY,
            order_type=Order.OrderType.LIMIT,
            limit_price=1.1000
        )
        self.assertEqual(user_order.source, Order.OrderSource.USER)
        
        sim_order = Order(
            order_id=2,
            product="EUR/USD",
            quantity=5,
            side=Order.OrderSide.SELL,
            order_type=Order.OrderType.LIMIT,
            limit_price=1.1010,
            source=Order.OrderSource.SIMULATION
        )
        self.assertEqual(sim_order.source, Order.OrderSource.SIMULATION)

    def test_exchange_place_order_with_source(self):
        """Test that Exchange.place_order correctly handles source parameter"""
        # Place user order (default)
        user_order_id = self.exchange.place_order(
            "EUR/USD", 10, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1000
        )
        user_order = self.exchange.orders[user_order_id]
        self.assertEqual(user_order.source, Order.OrderSource.USER)
        
        # Place simulation order (explicit)
        sim_order_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1010,
            Order.OrderSource.SIMULATION
        )
        sim_order = self.exchange.orders[sim_order_id]
        self.assertEqual(sim_order.source, Order.OrderSource.SIMULATION)

    def test_generate_simulated_order(self):
        """Test simulated order generation"""
        current_price = 1.1000
        order = generate_simulated_order(self.test_product, current_price)
        
        self.assertIsInstance(order, Order)
        self.assertEqual(order.source, Order.OrderSource.SIMULATION)
        self.assertEqual(order.order_type, Order.OrderType.LIMIT)
        self.assertIsNotNone(order.limit_price)
        self.assertGreater(order.limit_price, 0)
        self.assertGreater(order.quantity, 0)
        self.assertLessEqual(order.quantity, 10)
        self.assertIn(order.side, [Order.OrderSide.BUY, Order.OrderSide.SELL])

    def test_clob_order_matching_basic(self):
        """Test basic CLOB order matching"""
        # Place a buy order
        buy_order_id = self.exchange.place_order(
            "EUR/USD", 10, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1050
        )
        
        # Place a sell order that should match
        sell_order_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1040
        )
        
        # Run CLOB matching
        matches = self.exchange.match_orders_clob()
        
        # Should have 2 matches (one for each order)
        self.assertEqual(len(matches), 2)
        
        # Check fills
        buy_order = self.exchange.orders[buy_order_id]
        sell_order = self.exchange.orders[sell_order_id]
        
        self.assertEqual(buy_order.filled_quantity, 5)
        self.assertEqual(sell_order.filled_quantity, 5)
        self.assertTrue(sell_order.is_filled())
        self.assertFalse(buy_order.is_filled())
        self.assertTrue(buy_order.is_active)
        self.assertFalse(sell_order.is_active)

    def test_clob_order_matching_partial_fill(self):
        """Test CLOB partial fill scenario"""
        # Place a large buy order
        buy_order_id = self.exchange.place_order(
            "EUR/USD", 20, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1050
        )
        
        # Place a smaller sell order
        sell_order_id = self.exchange.place_order(
            "EUR/USD", 8, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1040
        )
        
        matches = self.exchange.match_orders_clob()
        
        buy_order = self.exchange.orders[buy_order_id]
        sell_order = self.exchange.orders[sell_order_id]
        
        # Sell order should be fully filled, buy order partially filled
        self.assertEqual(sell_order.filled_quantity, 8)
        self.assertEqual(buy_order.filled_quantity, 8)
        self.assertTrue(sell_order.is_filled())
        self.assertFalse(buy_order.is_filled())
        self.assertEqual(buy_order.remaining_quantity(), 12)

    def test_clob_order_matching_no_match(self):
        """Test CLOB when orders don't match (prices don't cross)"""
        # Place orders that shouldn't match
        self.exchange.place_order(
            "EUR/USD", 10, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1000
        )
        self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1050
        )
        
        matches = self.exchange.match_orders_clob()
        
        # No matches should occur
        self.assertEqual(len(matches), 0)

    def test_clob_price_time_priority(self):
        """Test that CLOB matching follows price-time priority"""
        # Place multiple buy orders at different prices
        buy1_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1030
        )
        buy2_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1040  # Higher price
        )
        
        # Place sell order that can match both
        sell_id = self.exchange.place_order(
            "EUR/USD", 3, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1020
        )
        
        matches = self.exchange.match_orders_clob()
        
        # Higher priced buy order should match first
        buy2_order = self.exchange.orders[buy2_id]
        self.assertEqual(buy2_order.filled_quantity, 3)

    def test_clob_multiple_products(self):
        """Test CLOB matching across multiple products"""
        # Place orders for different products
        eur_buy_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1050
        )
        gbp_sell_id = self.exchange.place_order(
            "GBP/USD", 3, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.2500
        )
        
        # Add matching orders
        eur_sell_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1040
        )
        gbp_buy_id = self.exchange.place_order(
            "GBP/USD", 3, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.2510
        )
        
        matches = self.exchange.match_orders_clob()
        
        # Should have matches for both products
        self.assertEqual(len(matches), 4)  # 2 orders per match, 2 matches

    def test_get_market_data_clob_mode(self):
        """Test get_market_data in CLOB mode"""
        # Mock the random order generation to be deterministic
        with patch('market_data.random.randint', return_value=1), \
             patch('market_data.random.choice') as mock_choice, \
             patch('market_data.random.random', return_value=0.3):
            
            mock_choice.return_value = self.test_product
            
            # Get market data in CLOB mode
            market_data, matches = get_market_data(MarketDataSource.CLOB, verbosity=1, exchange=self.exchange)
            
            # Should return bid/ask data
            self.assertIn(f"{self.test_product.symbol}_bid", market_data)
            self.assertIn(f"{self.test_product.symbol}_ask", market_data)
            
            # Should have placed some simulated orders
            self.assertGreater(len(self.exchange.orders), 0)

    def test_clob_market_data_with_existing_orders(self):
        """Test CLOB market data extraction from existing order book"""
        # Place some orders manually
        self.exchange.place_order(
            "EUR/USD", 10, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1020
        )
        self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1010
        )
        self.exchange.place_order(
            "EUR/USD", 8, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1040
        )
        self.exchange.place_order(
            "EUR/USD", 3, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1050
        )
        
        # Get market data
        with patch('market_data.random.randint', return_value=0):  # Don't generate new orders
            market_data, matches = get_market_data(MarketDataSource.CLOB, verbosity=1, exchange=self.exchange)
        
        # Check that bid/ask reflect the order book
        self.assertEqual(market_data["EUR/USD_bid"], 1.1020)  # Best buy
        self.assertEqual(market_data["EUR/USD_ask"], 1.1040)  # Best sell

    def test_clob_requires_exchange_parameter(self):
        """Test that CLOB mode requires exchange parameter"""
        with self.assertRaises(ValueError) as context:
            get_market_data(MarketDataSource.CLOB, verbosity=1)
        
        self.assertIn("Exchange instance required", str(context.exception))

    def test_clob_empty_order_book_shows_none(self):
        """Test that empty order book displays None instead of synthetic prices"""
        # Empty exchange with no orders
        empty_exchange = Exchange({})
        
        # Get market data with no simulated order generation
        with patch('market_data.random.randint', return_value=0):  # Don't generate new orders
            market_data, matches = get_market_data(MarketDataSource.CLOB, verbosity=1, exchange=empty_exchange)
        
        # All products should show None for bid/ask since no orders exist
        for product in PRODUCTS:
            symbol = product.symbol
            self.assertIsNone(market_data.get(f"{symbol}_bid"), 
                             f"Expected None for {symbol}_bid when no orders exist")
            self.assertIsNone(market_data.get(f"{symbol}_ask"), 
                             f"Expected None for {symbol}_ask when no orders exist")

    def test_active_orders_only_shows_user_orders(self):
        """Test that get_user_active_orders excludes simulated orders"""
        # Place a user order
        user_order_id = self.exchange.place_order(
            "EUR/USD", 10, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1000
        )
        
        # Place a simulated order
        sim_order_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1050,
            Order.OrderSource.SIMULATION
        )
        
        # Get all active orders (should include both)
        all_orders = self.exchange.get_active_orders()
        self.assertIn(user_order_id, all_orders)
        self.assertIn(sim_order_id, all_orders)
        self.assertEqual(len(all_orders), 2)
        
        # Get user active orders (should only include user order)
        user_orders = self.exchange.get_user_active_orders()
        self.assertIn(user_order_id, user_orders)
        self.assertNotIn(sim_order_id, user_orders)
        self.assertEqual(len(user_orders), 1)
        
        # Verify the user order is correct
        user_order = user_orders[user_order_id]
        self.assertEqual(user_order.source, Order.OrderSource.USER)

    def test_simulated_vs_user_order_logging(self):
        """Test that simulated and user order matches are logged differently"""
        # Place user order
        user_order_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.BUY, Order.OrderType.LIMIT, 1.1050
        )
        
        # Place simulated order
        sim_order_id = self.exchange.place_order(
            "EUR/USD", 5, Order.OrderSide.SELL, Order.OrderType.LIMIT, 1.1040,
            Order.OrderSource.SIMULATION
        )
        
        # Capture log output
        with self.assertLogs('exchange', level='INFO') as log:
            matches = self.exchange.match_orders_clob()
        
        # Check that both user and sim orders are mentioned in logs
        log_output = ' '.join(log.output)
        self.assertIn('user', log_output)
        self.assertIn('sim', log_output)

if __name__ == '__main__':
    unittest.main()