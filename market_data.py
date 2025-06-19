from typing import Dict, List, Optional, Tuple, NamedTuple
from datetime import datetime, timedelta
import logging
import random
import time
from enum import Enum

from twelvedata.endpoints import TimeSeriesEndpoint, APIUsageEndpoint
from products import PRODUCTS, Product
from rate_limiter import RateLimiter

# Named tuple for volatile periods
VolatilePeriod = NamedTuple('VolatilePeriod', [
    ('start_time', datetime),
    ('duration_seconds', int),
    ('volatility_factor', float)
])

# Event direction constants
EVENT_DIRECTION_UP = 'up'
EVENT_DIRECTION_DOWN = 'down'

# Named tuple for market events
Event = NamedTuple('Event', [
    ('product', str),
    ('direction', str),
    ('magnitude', float),
    ('timestamp', datetime)
])

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

def apply_event_to_price(event: Event, price: float) -> float:
    """Apply market event to a price."""
    if event.direction == EVENT_DIRECTION_UP:
        return price * (1 + event.magnitude)
    else:
        return price * (1 - event.magnitude)

def generate_market_event(product: Product):
    """Generate a market event for a specific product."""
    direction = random.choice([EVENT_DIRECTION_UP, EVENT_DIRECTION_DOWN])
    magnitude = random.uniform(0, market_data_config.max_event_magnitude)
    event = Event(product.symbol, direction, magnitude, datetime.now())
    logger.info(f"Market event generated: {event.product} {event.direction} " + \
            f"{event.magnitude*100:.2f}% at {event.timestamp}")
    return event


class MarketDataConfig:
    def __init__(self,
                 initial_price_range: tuple = (0, 100),
                 modeled_price_delta_percent: float = 0.005,
                 z_score: float = 2.0,
                 min_bid_ask_spread: float = 0.01,
                 max_bid_ask_spread: float = 0.5,
                 events_per_minute: float = 1.0,  # Default: 1 event per minute
                 max_event_magnitude: float = 0.1,  # 10% max event size
                 event_jitter: float = 0.2,  # 20% jitter around target frequency
                 volatility_duration: int = 60,  # 60 seconds
                 volatility_duration_jitter: float = 0.2,  # 20% jitter around duration
                 volatility_factor: float = 2.0,  # Default volatility multiplier
                 volatility_frequency: float = 0.01):  # 1% chance per call
        """
        Initialize market data configuration.

        Args:
            events_per_minute: Average number of events per minute (can be fractional)
            event_jitter: Fractional jitter around the target frequency (0 to 1)
            volatility_duration: Nominal duration of volatile periods in seconds
            duration_jitter: Jitter around volatility duration (0 to 1)
            volatility_factor: Multiplier for volatility during volatile periods
            volatility_frequency: Probability of starting a volatile period
        """
        self.initial_price_range = initial_price_range
        self.modeled_price_delta_percent = modeled_price_delta_percent
        self.z_score = z_score
        self.min_bid_ask_spread = min_bid_ask_spread
        self.max_bid_ask_spread = max_bid_ask_spread
        self.max_event_magnitude = max_event_magnitude
        self.volatility_duration = volatility_duration
        self.volatility_duration_jitter = volatility_duration_jitter
        self.volatility_factor = volatility_factor
        self.volatility_frequency = volatility_frequency

        # Calculate event probability per second
        self.event_probability = events_per_minute / 60.0

        # Calculate jitter parameters
        self.event_jitter = event_jitter
        self.min_event_probability = self.event_probability * (1 - event_jitter)
        self.max_event_probability = self.event_probability * (1 + event_jitter)

        # Store base event probability for volatile periods
        self._base_event_probability = self.event_probability

        # Log configuration settings
        logger.debug(f"MarketDataConfig initialized with: " +
                     f"price_range={initial_price_range}, " +
                     f"z_score={self.z_score}, " +
                     f"modeled_price_delta_percent={modeled_price_delta_percent*100}%, " +
                     f"spread={min_bid_ask_spread}-{max_bid_ask_spread}, " +
                     f"events/min={events_per_minute}, " +
                     f"jitter={event_jitter*100}%, " +
                     f"volatility_duration={volatility_duration}s±{volatility_duration_jitter*100}%, " +
                     f"volatility_factor={volatility_factor}x, " +
                     f"volatility_frequency={volatility_frequency*100}%")



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
current_volatile_period: Optional[VolatilePeriod] = None

# Initialize previous_prices with initial prices from product definitions
previous_prices = {
    product.symbol: product.initial_price  # Default to 100 if no initial_price
    for product in PRODUCTS
}

# Log initialization
for product, price in previous_prices.items():
    logger.info(f"Initialized previous price for {product}: {price}")


def get_market_data(market_data_source='twelvedata', verbosity=1):
    """Fetch market data from Twelve Data API or return random prices when in none mode"""
    global current_volatile_period
    logger.info(f"Fetching market data (source={market_data_source}, verbosity={verbosity})")

    if market_data_source == 'none':
        # Generate probabilistic prices for all products
        data = {}

        for product in PRODUCTS:
            symbol = product.symbol.upper()

            # For first call, generate random initial price
            if not previous_prices:
                logger.error("previous_prices is empty")
            else:
                prev_price = previous_prices.get(symbol, random.uniform(*market_data_config.initial_price_range))

            # Check if we should start a new volatile period
            if random.random() < market_data_config.volatility_frequency:
                # Add jitter to duration
                jittered_duration = int(market_data_config.volatility_duration *
                                      (1 + market_data_config.volatility_duration_jitter * (random.random() - 0.5)))
                current_volatile_period = VolatilePeriod(
                    start_time=datetime.now(),
                    duration_seconds=jittered_duration,
                    volatility_factor=market_data_config.volatility_factor
                )
                logger.info(f"Entering volatile period for {jittered_duration} seconds")

                # Update event probability for volatile period
                market_data_config.event_probability = market_data_config._base_event_probability * \
                    market_data_config.volatility_factor

            # Check if current volatile period has ended
            if current_volatile_period and datetime.now() > current_volatile_period.start_time + \
               timedelta(seconds=current_volatile_period.duration_seconds):
                current_volatile_period = None
                logger.info("Volatile period ended")
                # Reset event probability to base value
                market_data_config.event_probability = market_data_config._base_event_probability

            # If in volatile period, adjust volatility
            if current_volatile_period:
                std_dev = market_data_config.model_std_dev(prev_price) * \
                    current_volatile_period.volatility_factor
            else:
                std_dev = market_data_config.model_std_dev(prev_price)

            # Generate a new event with probability
            event_prob = random.uniform(
                market_data_config.min_event_probability,
                market_data_config.max_event_probability
            )
            if random.random() < event_prob:
                event = generate_market_event(product)
                old_price = apply_event_to_price(event, prev_price)
                logger.info(f"Generated event: {event}. old_price is now: {old_price}")
            else:
                old_price = prev_price
                logger.info(f"No event generated for {symbol}")

            # Generate new price with exponential decay in tails
            # Ensure we never accept a negative price
            min_price = market_data_config.initial_price_range[0]
            while True:
                new_price = random.gauss(old_price, std_dev)
                logger.info(f"old_price: {old_price}, std_dev: {std_dev}, new_price: {new_price}")
                if new_price >= min_price:  # Ensure price is at least minimum
                    break

            # If we got here, we have a valid positive price
            base_price = round(new_price, 2)

            # Ensure base price is at least minimum
            min_price = market_data_config.initial_price_range[0]
            base_price = max(base_price, min_price)
            logger.info(f"min price: {min_price}, final base price: {base_price}")

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
                f"Current API credit usage: {usage_data.get('current_usage', 'N/A')}/{usage_data.get('plan_limit', 'N/A')}; "
                f"Daily API credit usage: {usage_data.get('daily_usage', 'N/A')}/{usage_data.get('plan_daily_limit', 'N/A')}")
            if usage_data.get('current_usage', 0) >= usage_data.get('plan_limit', 0) or \
                usage_data.get('daily_usage', 0) >= usage_data.get('plan_daily_limit', 0):
                logger.warning("No credits remaining! Please upgrade your plan or wait for credits to reset.")
                return {}

        # Fetch market data for each product
        data = {}
        for product in PRODUCTS:
            ts_endpoint = TimeSeriesEndpoint(client)
            ts_endpoint.init(
                product=product.symbol.upper(),
                interval="1min",
                outputsize=1,
                timezone="UTC"
            )
            # Log event direction
            logger.info(f"Generating market event with direction {EVENT_DIRECTION_UP} for product {product.symbol}")

            try:
                df = ts_endpoint.get().as_json()
                if df:
                    data[f"{product.symbol.upper()}_bid"] = float(df[0]['high'])
                    data[f"{product.symbol.upper()}_ask"] = float(df[0]['low'])
                else:
                    logger.warning(f"No data returned for {product.symbol}")
                    data[f"{product.symbol.upper()}_bid"] = 'N/A'
                    data[f"{product.symbol.upper()}_ask"] = 'N/A'
            except Exception as e:
                logger.error(f"Error fetching {product.symbol}: {str(e)}")
                data[f"{product.symbol.upper()}_bid"] = 'N/A'
                data[f"{product.symbol.upper()}_ask"] = 'N/A'

        return data
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return {}


def get_market_data(market_data_source='twelvedata', verbosity=1):
    """Fetch market data from Twelve Data API or return random prices when in none mode"""
    global current_volatile_period
    logger.info(f"Fetching market data (source={market_data_source}, verbosity={verbosity})")

    if market_data_source == 'none':
        # Generate probabilistic prices for all products
        data = {}

        for product in PRODUCTS:
            symbol = product.symbol.upper()

            # For first call, generate random initial price
            if not previous_prices:
                logger.error("previous_prices is empty")
            else:
                prev_price = previous_prices.get(symbol, random.uniform(*market_data_config.initial_price_range))

            # Check if we should start a new volatile period
            if random.random() < market_data_config.volatility_frequency:
                # Add jitter to duration
                jittered_duration = int(market_data_config.volatility_duration *
                                      (1 + market_data_config.volatility_duration_jitter * (random.random() - 0.5)))
                current_volatile_period = VolatilePeriod(
                    start_time=datetime.now(),
                    duration_seconds=jittered_duration,
                    volatility_factor=market_data_config.volatility_factor
                )
                logger.info(f"Entering volatile period for {jittered_duration} seconds")

                # Update event probability for volatile period
                market_data_config.event_probability = market_data_config._base_event_probability * \
                    market_data_config.volatility_factor

            # Check if current volatile period has ended
            if current_volatile_period and datetime.now() > current_volatile_period.start_time + \
               timedelta(seconds=current_volatile_period.duration_seconds):
                current_volatile_period = None
                logger.info("Volatile period ended")
                # Reset event probability to base value
                market_data_config.event_probability = market_data_config._base_event_probability

            # If in volatile period, adjust volatility
            std_dev = market_data_config.model_std_dev(prev_price)
            if current_volatile_period:
                std_dev *= current_volatile_period.volatility_factor

            # Generate a new event with probability
            event_prob = random.uniform(
                market_data_config.min_event_probability,
                market_data_config.max_event_probability
            )
            if random.random() < event_prob:
                event = generate_market_event(product)
                old_price = apply_event_to_price(event, prev_price)
                logger.info(f"Generated event: {event}. old_price is now: {old_price}")
            else:
                old_price = prev_price
                logger.info(f"No event generated for {symbol}")

            # Generate new price with exponential decay in tails
            
	    # Ensure we never accept a negative price
            min_price = market_data_config.initial_price_range[0]
            while True:
                new_price = random.gauss(old_price, std_dev)
                logger.info(f"old_price: {old_price}, std_dev: {std_dev}, new_price: {new_price}")
                if new_price >= min_price:  # Ensure price is at least minimum
                    break

            # If we got here, we have a valid positive price
            base_price = round(new_price, 2)

            # Ensure base price is at least minimum
            min_price = market_data_config.initial_price_range[0]
            base_price = max(base_price, min_price)
            logger.info(f"min price: {min_price}, final base price: {base_price}")

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
            previous_prices[symbol] = base_price  # Store base price (midpoint) for next iteration

        return data

    get_market_data_from_twelvedata()
