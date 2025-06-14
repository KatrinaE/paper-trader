from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

@dataclass
class Order:
    """Represents a buy/sell order"""
    product: str
    quantity: int
    side: str  # 'buy' or 'sell'

class Fill:
    """Represents the execution of an order"""
    def __init__(self, product: str, quantity: int, side: str, price: float):
        self.product = product
        self.quantity = quantity
        self.side = side
        self.price = price
        self.timestamp = datetime.now()

class TradingBook:
    """Manages the user's portfolio and cash balance"""
    def __init__(self, initial_cash: float = 10000.0):
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # product -> quantity
        self.history: list[Fill] = []  # List of all fills

    def get_position(self, product: str) -> int:
        """Get the quantity held for a product"""
        return self.positions.get(product, 0)

    def add_to_position(self, product: str, quantity: int):
        """Add quantity to an existing product position"""
        self.positions[product] = self.positions.get(product, 0) + quantity

    def remove_from_position(self, product: str, quantity: int):
        """Remove quantity from an existing product position"""
        if self.get_position(product) < quantity:
            raise ValueError(f"Insufficient shares to sell {quantity} of {product}")
        self.positions[product] = self.positions.get(product, 0) - quantity
        if self.positions[product] == 0:
            del self.positions[product]

    def get_total_value(self, market_data: Dict[str, float]) -> float:
        """Calculate the total value of the portfolio"""
        total = self.cash
        for product, quantity in self.positions.items():
            price = market_data.get(f"{product}_bid", 0.0)
            total += quantity * price
        return total

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
