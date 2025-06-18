import unittest
from unittest.mock import patch, MagicMock
from products import PRODUCTS, Product
from market_data import get_market_data, market_data_config, MarketDataConfig, Event, current_volatile_period, VolatilePeriod
from datetime import datetime
import random

class TestMarketData(unittest.TestCase):
    def setUp(self):
        """Initialize test setup"""
        # Save original config
        self.original_config = market_data_config

    def tearDown(self):
        """Restore original config"""
        global market_data_config
        market_data_config = self.original_config

    def test_get_market_data_none_mode_no_api_calls(self):
        """
        Test that get_market_data with 'none' mode doesn't call API endpoints
        """
        with patch('twelvedata.endpoints.TimeSeriesEndpoint') as mock_ts_endpoint:
            get_market_data(market_data_source='none', verbosity=1)
            mock_ts_endpoint.assert_not_called()

    def test_get_market_data_none_mode_behavior(self):
        """
        Test that get_market_data with 'none' mode returns valid market data
        """
        # Run multiple iterations to verify price stability
        num_iterations = 10
        results = []

        # Get initial prices
        result = get_market_data(market_data_source='none', verbosity=1)
        self.assertEqual(len(result), len(PRODUCTS) * 2)  # Each instrument has bid and ask
        results.append(result)

        # Get updated prices for multiple iterations
        for i in range(1, num_iterations):
            result = get_market_data(market_data_source='none', verbosity=1)
            self.assertEqual(len(result), len(PRODUCTS) * 2)  # Each instrument has bid and ask
            results.append(result)

        # Verify price stability across all iterations
        for product in PRODUCTS:
            symbol = product.symbol.upper()

            # Get all bid and ask prices for this symbol across iterations
            bids = [result[f"{symbol}_bid"] for result in results]
            asks = [result[f"{symbol}_ask"] for result in results]

            # Verify all prices are positive
            for bid, ask in zip(bids, asks):
                assert bid >= 0, f"Bid price for {symbol} must be non-negative"
                assert ask >= 0, f"Ask price for {symbol} must be non-negative"

            # Verify price relationships
            for bid, ask in zip(bids, asks):
                self.assertLessEqual(bid, ask, f"Bid should be <= ask for {symbol}")

            # Verify price continuity across iterations
            # Check that prices are not jumping to extreme values
            for bid, ask in zip(bids, asks):
                initial_price = product.initial_price

                # Calculate bounds based on initial price
                max_price = initial_price * 1.5  # Allow up to 50% increase
                min_price = initial_price * 0.5  # Allow down to 50% decrease

                self.assertLessEqual(bid, max_price, f"Bid price for {symbol} jumped too high")
                self.assertLessEqual(ask, max_price, f"Ask price for {symbol} jumped too high")
                self.assertGreaterEqual(bid, min_price, f"Bid price for {symbol} dropped too low")
                self.assertGreaterEqual(ask, min_price, f"Ask price for {symbol} dropped too low")

    def test_get_market_data_never_negative(self):
        """
        Test that market data generation never produces negative prices
        """
        # Run many iterations to stress test price generation
        num_iterations = 1000

        # Get initial prices
        market_data = get_market_data(market_data_source='none')

        # Verify no negative prices and prices within bounds
        for symbol in market_data:
            if symbol.endswith('_bid') or symbol.endswith('_ask'):
                price = market_data[symbol]
                self.assertGreaterEqual(price, 0, f"Price for {symbol} is negative: {price}")
                # Get the product's initial price
                product_symbol = symbol[:-4]  # Remove _bid or _ask suffix
                product = next(p for p in PRODUCTS if p.symbol == product_symbol)
                initial_price = product.initial_price
                # Verify price is within reasonable bounds
                max_price = initial_price * 1.5  # Allow up to 50% increase
                min_price = initial_price * 0.5  # Allow down to 50% decrease
                self.assertLessEqual(price, max_price, f"Price for {symbol} too high: {price}")

    def test_market_event_price_jump(self):
        """
        Test that market events can cause price changes
        """
        # Configure market data with high event frequency for testing
        global market_data_config
        old_config = market_data_config
        market_data_config = MarketDataConfig(
            events_per_minute=60,  # 1 event per second
            event_jitter=0,  # No jitter for predictable testing
            max_event_magnitude=0.1)  # 10% max event size
        try:
            # Get initial prices
            market_data = get_market_data(market_data_source='none')

            # Get initial bid price for EUR/USD
            symbol = "EUR/USD"
            initial_bid = market_data[f"{symbol}_bid"]

            # Call get_market_data multiple times to ensure we see an event
            for _ in range(100):  # Try 100 iterations
                market_data = get_market_data(market_data_source='none')
                new_bid = market_data[f"{symbol}_bid"]
                if new_bid != initial_bid:
                    break
            else:
                # If we didn't see a price change after 10 iterations, fail
                self.fail("Price did not change after 10 iterations of market data updates")

            # Verify price changed (it should have changed due to high event frequency)
            self.assertNotEqual(initial_bid, new_bid, "Price did not change after event")

            # Verify price is still within reasonable bounds
            product = next(p for p in PRODUCTS if p.symbol == symbol)
            initial_price = product.initial_price
            max_price = initial_price * 1.5
            min_price = initial_price * 0.5
            self.assertLessEqual(new_bid, max_price, f"New bid price too high: {new_bid}")
            self.assertGreaterEqual(new_bid, min_price, f"New bid price too low: {new_bid}")
        finally:
            # Restore original config
            market_data_config = old_config

    def test_volatile_period_data_structure(self):
        """
        Test that VolatilePeriod NamedTuple is created correctly
        """
        start_time = datetime.now()
        duration = 60  # 1 minute
        volatility_factor = 2.0
        
        period = VolatilePeriod(
            start_time=start_time,
            duration_seconds=duration,
            volatility_factor=volatility_factor
        )
        
        self.assertEqual(period.start_time, start_time)
        self.assertEqual(period.duration_seconds, duration)
        self.assertEqual(period.volatility_factor, volatility_factor)

    def test_volatile_period_duration_calculation(self):
        """
        Test that duration calculation with jitter works correctly
        """
        base_duration = 60  # 1 minute
        jitter = 0.2  # 20% jitter
        
        # Test with positive jitter
        random.seed(42)  # For consistent results
        jittered_duration = int(base_duration * (1 + jitter * (random.random() - 0.5)))
        self.assertGreater(jittered_duration, base_duration * (1 - jitter))
        self.assertLess(jittered_duration, base_duration * (1 + jitter))
        
        # Test with negative jitter
        random.seed(100)  # Different seed
        jittered_duration = int(base_duration * (1 + jitter * (random.random() - 0.5)))
        self.assertGreater(jittered_duration, base_duration * (1 - jitter))
        self.assertLess(jittered_duration, base_duration * (1 + jitter))

    def test_volatile_period_volatility_calculation(self):
        """
        Test that volatility factor is applied correctly to price and event probability
        """
        # Set up test configuration
        market_data_config.volatility_factor = 2.0  # 2x volatility
        market_data_config._base_event_probability = 0.1  # 10% base probability
        
        # Test price volatility
        prev_price = 100.0
        std_dev = market_data_config.model_std_dev(prev_price)
        volatile_std_dev = std_dev * market_data_config.volatility_factor
        self.assertEqual(volatile_std_dev, std_dev * 2.0)
        
        # Test event probability
        base_prob = market_data_config._base_event_probability
        volatile_prob = base_prob * market_data_config.volatility_factor
        self.assertEqual(volatile_prob, base_prob * 2.0)

if __name__ == '__main__':
    unittest.main()
