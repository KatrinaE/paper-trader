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