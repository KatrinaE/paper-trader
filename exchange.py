import logging
from typing import Dict

from trading import Order, Fill

# Configure exchange logger
logger = logging.getLogger('exchange')

class Exchange:
    """Handles order execution and market data integration"""
    def __init__(self, market_data: Dict[str, float]):
        logger.info("Initializing Exchange")
        self.market_data = market_data

    def execute_order(self, order: Order) -> Fill:
        """Execute an order using current market data"""
        logger.info(f"Executing {order.side} order for {order.quantity} {order.product}")

        price = None
        if order.side == 'buy':
            price = self.market_data.get(f"{order.product}_ask", None)
        elif order.side == 'sell':
            price = self.market_data.get(f"{order.product}_bid", None)

        if price is None:
            logger.error(f"No market data available for {order.product}")
            raise ValueError(f"No market data available for {order.product}")

        # Convert price to float if it's a string
        if isinstance(price, str):
            try:
                price = float(price)
            except ValueError:
                raise ValueError(f"Invalid price format for {order.product}: {price}")

        fill = Fill(order.product, order.quantity, order.side, price)
        logger.info(f"Order executed: {fill.product} {fill.quantity} {fill.side} @ {fill.price}")
        return fill

    def update_market_data(self, new_data: Dict[str, float]):
        """Update the market data"""
        logger.info("Updating market data")
        self.market_data = new_data
