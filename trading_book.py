from typing import Dict

from trading import Fill

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