import logging
from typing import Dict, List, Tuple, Optional
from trading import Order, Fill

# Configure exchange logger
logger = logging.getLogger('exchange')

class Exchange:
    """Handles order execution, market data integration, and order book management."""
    def __init__(self, market_data: Dict[str, float]):
        logger.info("Initializing Exchange")
        self.market_data = market_data
        self.orders: Dict[int, Order] = {}  # order_id -> Order
        self.buy_orders: Dict[str, List[Order]] = {}  # product -> sorted list of buy orders
        self.sell_orders: Dict[str, List[Order]] = {}  # product -> sorted list of sell orders
        self.next_order_id = 1

    def get_next_order_id(self) -> int:
        """Get the next available order ID"""
        current_id = self.next_order_id
        self.next_order_id += 1
        return current_id

    def place_order(self, product: str, quantity: int, side: Order.OrderSide,
                   order_type: Order.OrderType = Order.OrderType.MARKET,
                   limit_price: Optional[float] = None) -> int:
        """Place a new order in the exchange's order book

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

    def execute_order(self, order: Order) -> Fill:
        """Execute an order using current market data"""
        logger.info(f"Executing {order.side} order for {order.quantity} {order.product}")

        # Place the order in the book
        order_id = self.place_order(
            order.product,
            order.quantity,
            order.side,
            order.order_type,
            order.limit_price
        )

        # Match orders against current market data
        matches = self.match_orders()

        # If we got a match, return the fill
        if matches:
            for matched_order, fill in matches:
                if matched_order.order_id == order_id:
                    return fill

        # If no match was found, return None
        return None

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order on the exchange

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

        # Remove from buy/sell orders list
        orders_list = self.buy_orders[order.product] if order.is_buy() else self.sell_orders[order.product]
        if order in orders_list:
            orders_list.remove(order)

        # Sort the orders list to maintain proper order
        if order.is_buy():
            self.buy_orders[order.product].sort(key=lambda x: (-x.limit_price if x.limit_price else float('inf'), x.timestamp))
        else:
            self.sell_orders[order.product].sort(key=lambda x: (x.limit_price if x.limit_price else 0, x.timestamp))

        order.is_active = False
        return True

    def get_active_orders(self) -> Dict[int, Order]:
        """Get all active orders in the exchange's order book"""
        logger.info("Getting active orders")
        active_orders = {oid: order for oid, order in self.orders.items() if order.is_active}
        logger.info(f"Active orders: {active_orders}")
        return active_orders

    def match_orders(self) -> List[Tuple[Order, Fill]]:
        """Match orders against current market data"""
        matches = []
        MAX_FILL_QUANTITY = 100

        for product in self.market_data.keys():
            if product.endswith('_bid'):
                symbol = product[:-4]
                bid_price = self.market_data[product]
                ask_price = self.market_data[f"{symbol}_ask"]

                # Match buy orders (market and limit)
                if symbol in self.buy_orders:
                    for order in self.buy_orders[symbol]:
                        if not order.is_active or order.is_filled():
                            continue

                        # Market orders always execute at ask price
                        # Limit orders only execute if ask price <= limit price
                        if (order.is_market() or (order.limit_price is not None and ask_price <= order.limit_price)) and order.remaining_quantity() > 0:
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

                        # Market orders always execute at bid price
                        # Limit orders only execute if limit price <= bid price
                        if (order.is_market() or (order.limit_price is not None and order.limit_price <= bid_price)) and order.remaining_quantity() > 0:
                            fill_quantity = min(order.remaining_quantity(), MAX_FILL_QUANTITY)
                            fill = Fill(symbol, fill_quantity, order.side, bid_price)
                            matches.append((order, fill))

                            order.filled_quantity += fill_quantity
                            if order.is_filled():
                                order.is_active = False

        return matches

    def update_market_data(self, new_data: Dict[str, float]):
        """Update the market data"""
        logger.info("Updating market data")
        self.market_data = new_data
