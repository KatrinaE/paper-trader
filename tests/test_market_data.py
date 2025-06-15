import unittest
from unittest.mock import patch, MagicMock
from main import PRODUCTS
from market_data import get_market_data

class TestMarketData(unittest.TestCase):
    def test_get_market_data_none_mode(self):
        """
        Test that get_market_data with 'none' mode returns random prices
        and doesn't call API endpoints
        """

        # Mock the TimeSeriesEndpoint
        with patch('twelvedata.endpoints.TimeSeriesEndpoint') as mock_ts_endpoint:

            # Call the function with 'none' mode
            result = get_market_data(market_data_source='none', verbosity=1)

            # Verify that TimeSeriesEndpoint was not instantiated
            mock_ts_endpoint.assert_not_called()

            # Verify that we got random prices for all instruments
            self.assertEqual(len(result), len(PRODUCTS) * 2)  # Each instrument has bid and ask

            # Verify that all prices are numbers (not strings)
            for key, value in result.items():
                if '_bid' in key or '_ask' in key:
                    self.assertIsInstance(value, (int, float))
                    self.assertGreaterEqual(value, 0)

if __name__ == '__main__':
    unittest.main()
