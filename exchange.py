from typing import Dict

from trading import Order, Fill

class Exchange:
    """Handles order execution and market data integration"""
    def __init__(self, market_data: Dict[str, float]):
        self.market_data = market_data

    def execute_order(self, order: Order) -> Fill:
        """Execute an order using current market data"""
        price = None
        if order.side == 'buy':
            price = self.market_data.get(f"{order.product}_ask", None)
        elif order.side == 'sell':
            price = self.market_data.get(f"{order.product}_bid", None)

        if price is None:
            raise ValueError(f"No market data available for {order.product}")

        # Convert price to float if it's a string
        if isinstance(price, str):
            try:
                price = float(price)
            except ValueError:
                raise ValueError(f"Invalid price format for {order.product}: {price}")

        return Fill(order.product, order.quantity, order.side, price)

    def update_market_data(self, new_data: Dict[str, float]):
        """Update the market data"""
        self.market_data = new_data
