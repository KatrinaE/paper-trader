import random
import logging
from datetime import datetime

from twelvedata.endpoints import TimeSeriesEndpoint, APIUsageEndpoint

from products import PRODUCTS
from rate_limiter import RateLimiter

# Configure logging
# Configure logging to only use stream handler
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('market_data')

# Rate limiting constants
MAX_CALLS_PER_MINUTE = 8
CALL_WINDOW_SECONDS = 60  # 1 minute

# Initialize rate limiter
rate_limiter = RateLimiter(MAX_CALLS_PER_MINUTE, CALL_WINDOW_SECONDS)

# Market data configuration
class MarketDataConfig:
    def __init__(self,
                 initial_price_range: tuple = (0, 100),
                 modeled_price_delta_percent: float = 0.005,
                 z_score: float = 2.0,
                 min_bid_ask_spread: float = 0.01,
                 max_bid_ask_spread: float = 0.5):
        self.initial_price_range = initial_price_range

        self.modeled_price_delta_percent = modeled_price_delta_percent
        self.z_score = z_score

        self.min_bid_ask_spread = min_bid_ask_spread
        self.max_bid_ask_spread = max_bid_ask_spread

        # Log configuration settings
        logger.debug(f"Config initialized with settings:")
        logger.debug(f"  Initial price range: {initial_price_range}")
        logger.debug(f"  Z-score: {self.z_score}")
        logger.debug(f"  Modeled price delta percent: {modeled_price_delta_percent*100}%")
        logger.debug(f"  Bid-ask spread range: {min_bid_ask_spread}-{max_bid_ask_spread}")
        logger.debug(f"  Z-score: {self.z_score:.4f}")


    def model_std_dev(self, prev_price: float) -> float:
        """Model standard deviation based on current price and given price range and z-score.

        Model standard deviation based on equation σ = (x - μ) / z.
        In words: std dev = (value - mean) / z-score.
        For example, if we want a std dev such that our new price (a randomly picked value) will fall
        within +/- 5% of the old price 95% of the time,
        use x - μ = 0.05 * prev_price
        and z-score = 2 (95% confidence interval)
        """
        std_dev = self.modeled_price_delta_percent * prev_price / self.z_score
        logger.debug(f"Calculated std dev for previous price {prev_price}: {std_dev:.4f}")
        return std_dev

# Global config and state instances
market_data_config = MarketDataConfig()

# Initialize previous_prices with initial prices from product definitions
previous_prices = {
    product['symbol']: product.get('initial_price', 100)  # Default to 100 if no initial_price
    for product in PRODUCTS
}

# Log initialization
for symbol, price in previous_prices.items():
    logger.info(f"Initialized previous price for {symbol}: {price}")

def get_market_data(market_data_source='twelvedata', verbosity=1):
    """Fetch market data from Twelve Data API or return random prices when in none mode"""
    logger.info(f"Fetching market data (source={market_data_source}, verbosity={verbosity})")

    if market_data_source == 'none':
        # Generate probabilistic prices for all products
        data = {}

        for product in PRODUCTS:
            symbol = product['symbol'].upper()

            # For first call, generate random initial price
            if not previous_prices:
                logger.error("previous_prices is empty")
            else:
                # Get previous price (use bid as reference)
                logger.info(f"symbol: {symbol}")
                logger.info(f"previous_prices: {previous_prices}")
                # Ensure we use uppercase symbol to match previous_prices keys
                prev_price = previous_prices.get(symbol, random.uniform(*market_data_config.initial_price_range))
                logger.info(f"prev_price: {prev_price}")

                # Generate new price using normal distribution
                std_dev = market_data_config.model_std_dev(prev_price)

                # Generate new price with exponential decay in tails
                # Ensure we never accept a negative price
                min_price = market_data_config.initial_price_range[0]
                while True:
                    new_price = random.gauss(prev_price, std_dev)
                    logger.info(f"prev_price: {prev_price}, std_dev: {std_dev}, new_price: {new_price}")
                    if new_price >= min_price:  # Ensure price is at least minimum
                        break
                        
                # If we got here, we have a valid positive price
                base_price = round(new_price, 2)
                
                # Ensure base price is at least minimum
                logger.info(f"min price: {min_price}")
                base_price = max(base_price, min_price)

                # Generate bid and ask prices with bid slightly lower than ask
                # Use a multiple of the standard deviation for the spread
                spread = std_dev * 2  # Using 2x std dev as spread
                logger.info(f"Using spread: {spread}")
                
                # Ensure bid price is positive and ask price is valid
                bid = max(round(base_price - spread, 2), market_data_config.initial_price_range[0])
                ask = max(round(base_price + spread, 2), market_data_config.initial_price_range[0])
                
                # Store in data dictionary
                data[f"{symbol}_bid"] = bid
                data[f"{symbol}_ask"] = ask
                
                logger.info(f"Generated prices for {symbol}: base={base_price}, bid={bid}, ask={ask}")
                # Store in previous_prices dictionary with positive price
                previous_prices[symbol] = base_price  # Store base price (midpoint) for next iteration

        return data


    rate_limiter.wait_if_needed()
    try:
        if config is None:
            config = market_data_config
            logger.debug("Using default market data configuration")
        else:
            logger.debug("Using custom market data configuration")

        usage_endpoint = APIUsageEndpoint(client)
        usage_data = usage_endpoint.get().as_json()

        if verbosity >= 2:
            logger.info(f"API Usage: {usage_data['credits_used']}/{usage_data['credits_total']}")
            if usage_data['credits_used'] >= usage_data['credits_total']:
                logger.warning("API credits are exhausted")

            logger.info(
                f"Current API credit usage: {usage_data.get('current_usage', 'N/A')}/{usage_data.get('plan_limit', 'N/A')}" + \
                    f"; Daily API credit usage: {usage_data.get('daily_usage', 'N/A')}/{usage_data.get('plan_daily_limit', 'N/A')}")
            if usage_data.get('current_usage', 0) >= usage_data.get('plan_limit', 0) or \
                usage_data.get('daily_usage', 0) >= usage_data.get('plan_daily_limit', 0):
                logger.warning("No credits remaining! Please upgrade your plan or wait for credits to reset.")
                return {}

        # Fetch market data for each product
        data = {}
        for product in PRODUCTS:
            ts_endpoint = TimeSeriesEndpoint(client)
            ts_endpoint.init(
                symbol=product['symbol'],
                interval="1min",
                outputsize=1,
                timezone="UTC"
            )

            try:
                df = ts_endpoint.get().as_json()
                if len(df) > 0:
                    data[f"{product['symbol'].upper()}_bid"] = float(df[0]['high'])
                    data[f"{product['symbol'].upper()}_ask"] = float(df[0]['low'])
                else:
                    logger.warning(f"No data returned for {product['symbol']}")
                    data[f"{product['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{product['symbol'].upper()}_ask"] = 'N/A'
            except Exception as e:
                if verbosity >= 1:
                    logger.error(f"Error fetching {product['symbol']}: {str(e)}")
                    data[f"{product['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{product['symbol'].upper()}_ask"] = 'N/A'

        return data
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return {}