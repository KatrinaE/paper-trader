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

    order_id: int
    product: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    limit_price: Optional[float] = None  # Only used for LIMIT orders
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

class OrderBook:
    """Manages all orders (market and limit) for all products"""
    def __init__(self):
        self.orders: Dict[int, Order] = {}  # order_id -> Order
        self.buy_orders: Dict[str, List[Order]] = {}  # product -> sorted list of buy orders
        self.sell_orders: Dict[str, List[Order]] = {}  # product -> sorted list of sell orders
        self.next_order_id = 1
        self.logger = logging.getLogger('order_book')

    def place_order(self, product: str, quantity: int, side: Order.OrderSide,
                   order_type: Order.OrderType = Order.OrderType.MARKET,
                   limit_price: Optional[float] = None) -> int:
        """Place a new order

        Args:
            product: The product symbol
            quantity: Number of shares
            side: BUY or SELL
            order_type: MARKET or LIMIT
            limit_price: Required for LIMIT orders

        Returns:
            The order ID of the placed order
        """
        if order_type == Order.OrderType.LIMIT and limit_price is None:
            raise ValueError("Limit price is required for LIMIT orders")

        order_id = self.next_order_id
        self.next_order_id += 1

        order = Order(
            order_id=order_id,
            product=product,
            quantity=quantity,
            side=side,
            order_type=order_type,
            limit_price=limit_price
        )

        self.orders[order_id] = order

        # Add to appropriate order book
        if side == Order.OrderSide.BUY:
            if product not in self.buy_orders:
                self.buy_orders[product] = []
            self.buy_orders[product].append(order)
            # Sort buy orders by price (highest first) and then by timestamp
            self.buy_orders[product].sort(key=lambda x: (-x.limit_price if x.limit_price else float('inf'), x.timestamp))
        else:  # SELL
            if product not in self.sell_orders:
                self.sell_orders[product] = []
            self.sell_orders[product].append(order)
            # Sort sell orders by price (lowest first) and then by timestamp
            self.sell_orders[product].sort(key=lambda x: (x.limit_price if x.limit_price else 0, x.timestamp))

        return order_id

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order

        Args:
            order_id: The ID of the order to cancel

        Returns:
            True if order was successfully cancelled, False if order not found or already cancelled
        """
        if order_id not in self.orders:
            return False

        order = self.orders[order_id]
        if not order.is_active:
            return False

        order.is_active = False
        return True

    def match_orders(self, market_data: Dict[str, float]) -> List[Tuple[Order, Fill]]:
        """Match orders against current market data

        Args:
            market_data: Dictionary containing bid and ask prices for products

        Returns:
            List of tuples containing (order, fill) for each matched order
        """
        matches = []
        MAX_FILL_QUANTITY = 100

        for product in market_data.keys():
            if product.endswith('_bid'):
                symbol = product[:-4]
                bid_price = market_data[product]
                ask_price = market_data[f"{symbol}_ask"]

                # Match buy orders (market and limit)
                if symbol in self.buy_orders:
                    for order in self.buy_orders[symbol]:
                        if not order.is_active or order.is_filled():
                            continue

                        if (order.is_market() or order.limit_price >= ask_price) and order.remaining_quantity() > 0:
                            fill_quantity = min(order.remaining_quantity(), MAX_FILL_QUANTITY)
                            fill = Fill(symbol, fill_quantity, order.side, ask_price)
                            matches.append((order, fill))

                            order.filled_quantity += fill_quantity
                            if order.is_filled():
                                order.is_active = False

                # Match sell orders (market and limit)
                if symbol in self.sell_orders:
                    for order in self.sell_orders[symbol]:
                        if not order.is_active or order.is_filled():
                            continue

                        if (order.is_market() or order.limit_price <= bid_price) and order.remaining_quantity() > 0:
                            fill_quantity = min(order.remaining_quantity(), MAX_FILL_QUANTITY)
                            fill = Fill(symbol, fill_quantity, order.side, bid_price)
                            matches.append((order, fill))

                            order.filled_quantity += fill_quantity
                            if order.is_filled():
                                order.is_active = False

        return matches

    def get_active_orders(self) -> Dict[int, Order]:
        """Get all active orders"""
        return {oid: order for oid, order in self.orders.items() if order.is_active}
