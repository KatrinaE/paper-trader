import logging
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from enum import Enum

@dataclass
class Order:
    """Represents a buy/sell order"""
    class OrderType(Enum):
        MARKET = "market"  # Fill at current market price
        LIMIT = "limit"   # Fill only if price is better than limit price

    class OrderSide(Enum):
        BUY = "buy"
        SELL = "sell"

    class OrderSource(Enum):
        USER = "user"
        SIMULATION = "simulation"

    order_id: int
    product: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    limit_price: Optional[float] = None  # Only used for LIMIT orders
    source: OrderSource = OrderSource.USER
    timestamp: datetime = datetime.now()
    filled_quantity: int = 0
    is_active: bool = True

    def __post_init__(self):
        if self.order_type == Order.OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit price is required for LIMIT orders")

    def is_buy(self) -> bool:
        return self.side == Order.OrderSide.BUY

    def is_sell(self) -> bool:
        return self.side == Order.OrderSide.SELL

    def is_limit(self) -> bool:
        return self.order_type == Order.OrderType.LIMIT

    def is_market(self) -> bool:
        return self.order_type == Order.OrderType.MARKET

    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

class Fill:
    """Represents the execution of an order"""
    def __init__(self, product: str, quantity: int, side: Order.OrderSide, price: float):
        self.product = product
        self.quantity = quantity
        self.side = side
        self.price = price
        self.timestamp = datetime.now()
