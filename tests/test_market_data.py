import unittest
from unittest.mock import patch, MagicMock
from main import PRODUCTS
from market_data import get_market_data, market_data_config, MarketDataConfig

class TestMarketData(unittest.TestCase):
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
            symbol = product['symbol'].upper()
            
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
                # Verify that prices are within reasonable bounds
                # We're using the initial price range from market_data_config as a reference
                max_price = market_data_config.initial_price_range[1]
                min_price = market_data_config.initial_price_range[0]
                self.assertLessEqual(bid, max_price * 1.5, f"Bid price for {symbol} jumped too high")
                self.assertLessEqual(ask, max_price * 1.5, f"Ask price for {symbol} jumped too high")
                self.assertGreaterEqual(bid, min_price * 0.5, f"Bid price for {symbol} dropped too low")
                self.assertGreaterEqual(ask, min_price * 0.5, f"Ask price for {symbol} dropped too low")

    def test_get_market_data_never_negative(self):
        """
        Test that market data generation never produces negative prices
        """
        # Run many iterations to stress test price generation
        num_iterations = 1000

        # Get initial prices
        result = get_market_data(market_data_source='none', verbosity=1)
        self.assertEqual(len(result), len(PRODUCTS) * 2)  # Each instrument has bid and ask
        
        # Get updated prices for many iterations
        prev_prices = {}  # Store previous prices for each symbol
        
        for i in range(1, num_iterations):
            result = get_market_data(market_data_source='none', verbosity=1)
            self.assertEqual(len(result), len(PRODUCTS) * 2)  # Each instrument has bid and ask
            
            # Verify all prices are positive
            for product in PRODUCTS:
                symbol = product['symbol'].upper()
                bid = result[f"{symbol}_bid"]
                ask = result[f"{symbol}_ask"]
                assert bid >=0, f"Iteration {i}: Bid price for {symbol} must be non-negative"
                assert ask >=0, f"Iteration {i}: Ask price for {symbol} must be non-negative"
                self.assertLessEqual(bid, ask, f"Iteration {i}: Bid should be <= ask for {symbol}")
                
                # Store prices as numbers
                self.assertIsInstance(bid, (int, float))
                self.assertIsInstance(ask, (int, float))
                
                # Verify price continuity with previous iteration
                if symbol in prev_prices:
                    prev_bid, prev_ask = prev_prices[symbol]
                    assert prev_bid >= 0, f"Previous bid price for {symbol} should be non-negative"
                    assert prev_ask >= 0, f"Previous ask price for {symbol} should be non-negative"
                    self.assertLessEqual(prev_bid, prev_ask, f"Previous bid should be <= ask for {symbol}")
                    
                    # Verify that prices are generally moving in a continuous manner
                    max_price = market_data_config.initial_price_range[1]
                    min_price = market_data_config.initial_price_range[0]
                    self.assertLessEqual(bid, max_price * 1.5, f"Bid price for {symbol} jumped too high")
                    self.assertLessEqual(ask, max_price * 1.5, f"Ask price for {symbol} jumped too high")
                    self.assertGreaterEqual(bid, min_price * 0.5, f"Bid price for {symbol} dropped too low")
                    self.assertGreaterEqual(ask, min_price * 0.5, f"Ask price for {symbol} dropped too low")
                
                # Store current prices for next iteration
                prev_prices[symbol] = (bid, ask)

if __name__ == '__main__':
    unittest.main()
