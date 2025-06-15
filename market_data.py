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
                 modeled_price_delta_percent: float = 0.05,
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

# Global config instance
market_data_config = MarketDataConfig()

def get_market_data(market_data_source='twelvedata', verbosity=1):
    """Fetch market data from Twelve Data API or return random prices when in none mode"""
    logger.info(f"Fetching market data (source={market_data_source}, verbosity={verbosity})")

    if market_data_source == 'none':
        # Generate probabilistic prices for all products
        data = {}
        previous_prices = {}  # Store previous prices to maintain continuity

        for product in PRODUCTS:
            symbol = product['symbol'].upper()

            # For first call, generate random initial price
            if not previous_prices:
                base_price = random.uniform(*market_data_config.initial_price_range)
            else:
                # Get previous price (use bid as reference)
                prev_price = previous_prices.get(symbol, random.uniform(*market_data_config.initial_price_range))

                # Generate new price using normal distribution
                std_dev = market_data_config.model_std_dev(prev_price)

                # Generate new price with exponential decay in tails
                while True:
                    new_price = random.gauss(prev_price, std_dev)
                    if new_price >= 0:  # Allow zero price
                        break

                base_price = round(new_price, 2)

            # Generate bid and ask prices with bid slightly lower than ask
            spread = random.uniform(market_data_config.min_bid_ask_spread, market_data_config.max_bid_ask_spread)
            bid = round(base_price - spread, 2)
            ask = round(base_price + spread, 2)

            data[f"{symbol}_bid"] = bid
            data[f"{symbol}_ask"] = ask
            previous_prices[symbol] = bid  # Store bid price for next iteration

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
            console.print(f"API Usage: {usage_data['credits_used']}/{usage_data['credits_total']}")
            if usage_data['credits_used'] >= usage_data['credits_total']:
                console.print("[red]WARNING: API credits are exhausted[/red]")

            console.print(
                f"[cyan]Current API credit usage: {usage_data.get('current_usage', 'N/A')}/{usage_data.get('plan_limit', 'N/A')}" + \
                    f"; Daily API credit usage: {usage_data.get('daily_usage', 'N/A')}/{usage_data.get('plan_daily_limit', 'N/A')} [/cyan]")
            if usage_data.get('current_usage', 0) >= usage_data.get('plan_limit', 0) or \
                usage_data.get('daily_usage', 0) >= usage_data.get('plan_daily_limit', 0):
                console.print("[red]No credits remaining! Please upgrade your plan or wait for credits to reset.[/red]")
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
                    data[f"{product['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{product['symbol'].upper()}_ask"] = 'N/A'
            except Exception as e:
                if verbosity >= 1:
                    console.print(f"Error fetching {product['symbol']}: {str(e)}")
                    data[f"{product['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{product['symbol'].upper()}_ask"] = 'N/A'

        return data
    except Exception as e:
        console.print(f"Error fetching data: {str(e)}")
        console.print(f"Full error details: {traceback.format_exc()}")
        return {}