import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import deque

from order import Fill, Order

# Configure trading book logger
logger = logging.getLogger('trading_book')

@dataclass
class Lot:
    """Represents a single lot (batch) of shares bought at the same time/price"""
    quantity: int
    price: float
    timestamp: datetime
    
    @property
    def total_cost(self) -> float:
        """Total cost of this lot"""
        return abs(self.quantity * self.price)

@dataclass
class Position:
    """Represents a position with FIFO lot tracking"""
    long_lots: deque = None  # Lots for long positions (FIFO queue)
    short_lots: deque = None  # Lots for short positions (FIFO queue) 
    realized_pnl: float = 0.0  # P&L from closed positions
    
    def __post_init__(self):
        if self.long_lots is None:
            self.long_lots = deque()
        if self.short_lots is None:
            self.short_lots = deque()
    
    @property
    def quantity(self) -> int:
        """Net quantity (positive = long, negative = short, 0 = flat)"""
        long_qty = sum(lot.quantity for lot in self.long_lots)
        short_qty = sum(lot.quantity for lot in self.short_lots)
        return long_qty - short_qty
    
    @property 
    def total_cost(self) -> float:
        """Total cost basis of current position"""
        long_cost = sum(lot.total_cost for lot in self.long_lots)
        short_cost = sum(lot.total_cost for lot in self.short_lots)
        return long_cost + short_cost
    
    @property
    def average_cost(self) -> float:
        """Calculate average cost per unit"""
        if self.quantity == 0:
            return 0.0
        return self.total_cost / abs(self.quantity)
    
    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L at current price using FIFO lots"""
        if self.quantity == 0:
            return 0.0
            
        unrealized = 0.0
        
        # Calculate unrealized P&L for each lot
        for lot in self.long_lots:
            unrealized += lot.quantity * (current_price - lot.price)
            
        for lot in self.short_lots:
            unrealized += lot.quantity * (lot.price - current_price)
            
        return unrealized
    
    def total_pnl(self, current_price: float) -> float:
        """Calculate total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl(current_price)
    
    def _close_lots_fifo(self, lots_queue: deque, quantity: int, price: float, is_closing_for_buy: bool) -> Tuple[int, float]:
        """
        Close lots from a queue using FIFO, return (remaining_quantity, realized_pnl)
        
        Args:
            lots_queue: The deque of lots to close from
            quantity: Number of shares to close
            price: Current trade price
            is_closing_for_buy: True if this is a buy closing short lots, False if sell closing long lots
        """
        remaining_quantity = quantity
        realized_pnl = 0.0
        
        while remaining_quantity > 0 and lots_queue:
            lot = lots_queue[0]  # First (oldest) lot
            
            if remaining_quantity >= lot.quantity:
                # Close entire lot
                close_qty = lot.quantity
                if is_closing_for_buy:
                    # Buying to close short position: profit = short_price - buy_price
                    lot_pnl = close_qty * (lot.price - price)
                else:
                    # Selling to close long position: profit = sell_price - long_price  
                    lot_pnl = close_qty * (price - lot.price)
                    
                realized_pnl += lot_pnl
                remaining_quantity -= close_qty
                lots_queue.popleft()  # Remove closed lot
                
                lot_type = "short" if is_closing_for_buy else "long"
                logger.info(f"Closed {lot_type} lot: {close_qty} @ {lot.price}, P&L: ${lot_pnl:.2f}")
                
            else:
                # Partially close lot
                if is_closing_for_buy:
                    lot_pnl = remaining_quantity * (lot.price - price)
                else:
                    lot_pnl = remaining_quantity * (price - lot.price)
                    
                realized_pnl += lot_pnl
                lot.quantity -= remaining_quantity
                
                lot_type = "short" if is_closing_for_buy else "long"
                logger.info(f"Partially closed {lot_type} lot: {remaining_quantity} @ {lot.price}, P&L: ${lot_pnl:.2f}")
                remaining_quantity = 0
        
        return remaining_quantity, realized_pnl

    def handle_buy(self, quantity: int, price: float, timestamp: datetime = None) -> float:
        """Handle a buy transaction - close short positions using FIFO, then add long position"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Close short positions first
        remaining_qty, realized_pnl = self._close_lots_fifo(self.short_lots, quantity, price, True)
        
        # Add remaining quantity as new long lot
        if remaining_qty > 0:
            new_lot = Lot(quantity=remaining_qty, price=price, timestamp=timestamp)
            self.long_lots.append(new_lot)
            logger.info(f"Added long lot: {remaining_qty} @ {price}")
        
        self.realized_pnl += realized_pnl
        return realized_pnl

    def handle_sell(self, quantity: int, price: float, timestamp: datetime = None) -> float:
        """Handle a sell transaction - close long positions using FIFO, then add short position"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Close long positions first  
        remaining_qty, realized_pnl = self._close_lots_fifo(self.long_lots, quantity, price, False)
        
        # Add remaining quantity as new short lot
        if remaining_qty > 0:
            new_lot = Lot(quantity=remaining_qty, price=price, timestamp=timestamp)
            self.short_lots.append(new_lot)
            logger.info(f"Added short lot: {remaining_qty} @ {price}")
        
        self.realized_pnl += realized_pnl
        return realized_pnl

class TradingBook:
    """Manages the user's portfolio and cash balance"""
    def __init__(self, initial_cash: float = 10000.0):
        logger.info(f"Initializing TradingBook with initial cash: {initial_cash}")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}  # product -> Position object
        self.history: list[Fill] = []  # List of all fills
        self.exchange = None  # Will be set by the client code

    def get_position(self, product: str) -> int:
        """Get the quantity held for a product"""
        position = self.positions.get(product, Position())
        return position.quantity
    
    def get_position_object(self, product: str) -> Position:
        """Get the Position object for a product"""
        if product not in self.positions:
            self.positions[product] = Position()
        return self.positions[product]

    def add_to_position(self, product: str, quantity: int, price: float):
        """Add quantity to position (handle buy transaction)"""
        logger.info(f"Adding {quantity} {product} to position at {price}")
        position = self.get_position_object(product)
        realized_pnl = position.handle_buy(quantity, price)
        logger.info(f"Realized P&L from buy: ${realized_pnl:.2f}")

    def remove_from_position(self, product: str, quantity: int, price: float):
        """Remove quantity from position (handle sell transaction)"""
        logger.info(f"Removing {quantity} {product} from position at {price}")
        position = self.get_position_object(product)
        
        # Check if we have enough shares (considering both long and potential short positions)
        if position.quantity < quantity:
            logger.error(f"Insufficient shares to sell {quantity} of {product}")
            raise ValueError(f"Insufficient shares to sell {quantity} of {product}")
        
        realized_pnl = position.handle_sell(quantity, price)
        logger.info(f"Realized P&L from sell: ${realized_pnl:.2f}")

    def get_total_value(self, market_data: Dict[str, float]) -> float:
        """Calculate the total value of the portfolio"""
        logger.info("Calculating total portfolio value")
        total = self.cash
        for product, position in self.positions.items():
            if position.quantity != 0:
                price = market_data.get(f"{product}_bid", 0.0)
                logger.debug(f"Position value: {product} x {position.quantity} @ {price}")
                total += position.quantity * price
        logger.info(f"Total portfolio value: {total}")
        return total
    
    def get_total_unrealized_pnl(self, market_data: Dict[str, float]) -> float:
        """Calculate total unrealized P&L"""
        total_unrealized = 0.0
        for product, position in self.positions.items():
            if position.quantity != 0:
                price = market_data.get(f"{product}_bid", 0.0)
                total_unrealized += position.unrealized_pnl(price)
        return total_unrealized
    
    def get_total_realized_pnl(self) -> float:
        """Calculate total realized P&L"""
        total_realized = 0.0
        for position in self.positions.values():
            total_realized += position.realized_pnl
        return total_realized
    
    def get_total_pnl(self, market_data: Dict[str, float]) -> float:
        """Calculate total P&L (realized + unrealized)"""
        return self.get_total_realized_pnl() + self.get_total_unrealized_pnl(market_data)

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

        if order_type == Order.OrderType.MARKET and limit_price is not None:
            raise ValueError("Limit price not allowed for MARKET orders")

        if side == Order.OrderSide.BUY:
            if self.cash < quantity * (limit_price if limit_price else self.exchange.market_data.get(f"{product}_ask", 0.0)):
                logger.error(f"Insufficient cash to place order for {quantity} {product}")
                raise ValueError("Insufficient cash")
        else:  # SELL
            if self.get_position(product) < quantity:
                logger.error(f"Insufficient shares to place order for {quantity} {product}")
                raise ValueError("Insufficient shares")

        # Place the order on the exchange
        return self.exchange.place_order(product, quantity, side, order_type, limit_price)

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order

        Args:
            order_id: The ID of the order to cancel

        Returns:
            True if order was successfully cancelled, False if order not found or already cancelled
        """
        return self.exchange.cancel_order(order_id)

    def process_fills(self, matches: List[Tuple[Order, Fill]]) -> List[Tuple[Order, Fill]]:
        """Process fills from provided matches"""
        for order, fill in matches:
            # Only process fills for user orders (ignore simulated order fills)
            if order.source == Order.OrderSource.USER:
                if order.is_buy():
                    self.cash -= fill.quantity * fill.price
                    self.add_to_position(fill.product, fill.quantity, fill.price)
                else:  # SELL
                    self.cash += fill.quantity * fill.price
                    self.remove_from_position(fill.product, fill.quantity, fill.price)

                self.history.append(fill)
                logger.info(f"Processed user fill for order {order.order_id}: {fill}")

        return matches

    def get_active_orders(self) -> Dict[int, Order]:
        """Get all active orders"""
        return self.exchange.get_active_orders()

    def get_user_active_orders(self) -> Dict[int, Order]:
        """Get only user active orders (exclude simulated orders)"""
        return self.exchange.get_user_active_orders()
