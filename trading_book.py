import logging
from typing import Dict, List, Optional, Tuple

from trading import Fill, Order, OrderBook

# Configure trading book logger
logger = logging.getLogger('trading_book')

class TradingBook:
    """Manages the user's portfolio and cash balance"""
    def __init__(self, initial_cash: float = 10000.0):
        logger.info(f"Initializing TradingBook with initial cash: {initial_cash}")
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # product -> quantity
        self.history: list[Fill] = []  # List of all fills
        self.order_book = OrderBook()

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

    def place_order(self, product: str, quantity: int, side: Order.OrderSide,
                   order_type: Order.OrderType = Order.OrderType.MARKET,
                   limit_price: Optional[float] = None) -> int:
        """Place a new order (market or limit)

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

        if side == Order.OrderSide.BUY:
            if self.cash < quantity * (limit_price if limit_price else market_data[f"{product}_ask"]):
                logger.error(f"Insufficient cash to place order for {quantity} {product}")
                raise ValueError("Insufficient cash")
        else:  # SELL
            if self.get_position(product) < quantity:
                logger.error(f"Insufficient shares to place order for {quantity} {product}")
                raise ValueError("Insufficient shares")

        return self.order_book.place_order(product, quantity, side, order_type, limit_price)

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order

        Args:
            order_id: The ID of the order to cancel

        Returns:
            True if order was successfully cancelled, False if order not found or already cancelled
        """
        return self.order_book.cancel_order(order_id)

    def process_market_data(self, market_data: Dict[str, float]) -> List[Tuple[Order, Fill]]:
        """Process market data and match orders

        Args:
            market_data: Dictionary containing bid and ask prices for products

        Returns:
            List of tuples containing (order, fill) for each matched order
        """
        matches = self.order_book.match_orders(market_data)
        for order, fill in matches:
            if order.is_buy():
                self.cash -= fill.quantity * fill.price
                self.add_to_position(fill.product, fill.quantity)
            else:  # SELL
                self.cash += fill.quantity * fill.price
                self.remove_from_position(fill.product, fill.quantity)

            self.history.append(fill)
            logger.info(f"Filled order {order.order_id}: {fill}")

        return matches

    def get_active_orders(self) -> Dict[int, Order]:
        """Get all active orders"""
        return self.order_book.get_active_orders()
