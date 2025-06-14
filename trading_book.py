import logging
from typing import Dict

from trading import Fill

# Configure trading book logger
logger = logging.getLogger('trading_book')

class TradingBook:
    """Manages the user's portfolio and cash balance"""
    def __init__(self, initial_cash: float = 10000.0):
        logger.info(f"Initializing TradingBook with initial cash: {initial_cash}")
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # product -> quantity
        self.history: list[Fill] = []  # List of all fills

    def get_position(self, product: str) -> int:
        """Get the quantity held for a product"""
        return self.positions.get(product, 0)

    def add_to_position(self, product: str, quantity: int):
        """Add quantity to an existing product position"""
        logger.info(f"Adding {quantity} {product} to position")
        self.positions[product] = self.positions.get(product, 0) + quantity

    def remove_from_position(self, product: str, quantity: int):
        """Remove quantity from an existing product position"""
        logger.info(f"Removing {quantity} {product} from position")
        if self.get_position(product) < quantity:
            logger.error(f"Insufficient shares to sell {quantity} of {product}")
            raise ValueError(f"Insufficient shares to sell {quantity} of {product}")
        self.positions[product] = self.positions.get(product, 0) - quantity
        if self.positions[product] == 0:
            del self.positions[product]
            logger.info(f"Position in {product} reduced to zero")

    def get_total_value(self, market_data: Dict[str, float]) -> float:
        """Calculate the total value of the portfolio"""
        logger.info("Calculating total portfolio value")
        total = self.cash
        for product, quantity in self.positions.items():
            price = market_data.get(f"{product}_bid", 0.0)
            logger.debug(f"Position value: {product} x {quantity} @ {price}")
            total += quantity * price
        logger.info(f"Total portfolio value: {total}")
        return total
