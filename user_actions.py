import logging
from rich.prompt import Prompt

from products import PRODUCTS, Product
from order import Order, Fill

from market_data import get_market_data, MarketDataSource, market_data_config
from exchange import Exchange
from trading_book import TradingBook

# Configure user actions logger
logger = logging.getLogger('user_actions')
BUY = 'buy'
SELL = 'sell'

def add_product(console):
    """Add a new product."""
    logger.info("Starting add_product")
    console.print("\n[bold]Add Product[/bold]")
    symbol = console.input("Enter symbol (e.g. EUR/USD): ")
    name = console.input("Enter name/description: ")

    # Loop until we get a valid category
    while True:
        category = console.input("Enter category (forex/commodities/stocks): ").lower()
        if category in ["forex", "commodities", "stocks"]:
            break
        console.print("[yellow]Oops! Please enter either 'forex', 'commodities', or 'stocks'.[/yellow]")

    _add_product(symbol, name, category)
    logger.info(f"Added product: {symbol} - {name} (Category: {category})")
    console.print(f"[green]Added {symbol} - {name} (Category: {category})[/green]")
    # No need to return a layout

def _add_product(symbol, name, category):
    # Use the same initial price as the default products
    initial_price = 100.0  # Default initial price
    PRODUCTS.append(Product(symbol=symbol, name=name, category=category, initial_price=initial_price))

def remove_product(console):
    """Remove an existing product."""
    logger.info("Starting remove_product")
    console.print("\n[bold]Remove Product[/bold]")
    console.print("Available products:")
    for config in PRODUCTS:
        console.print(f"{config['symbol']} - {config['name']} (Category: {config['category']})")

    # Keep asking until we get a valid symbol or user cancels
    while True:
        choice = console.input("Enter symbol to remove (or 'q' to cancel): ")
        if choice.lower() == 'q':
            logger.info("User cancelled remove product")
            return None

        try:
            removed_config = _remove_product(choice)
            logger.info(f"Removed product: {removed_config['symbol']} - {removed_config['name']} (Category: {removed_config['category']})")
            console.print(f"[green]Removed {removed_config['symbol']} - {removed_config['name']} (Category: {removed_config['category']})[/green]")
            return None
        except ProductNotFoundError:
            logger.info("Invalid symbol entered")
            console.print("[yellow]Invalid symbol. Please try again or enter 'q' to cancel.[/yellow]")

class ProductNotFoundError:
    pass

def _remove_product(choice):
    for i, config in enumerate(PRODUCTS):
        if config.symbol == choice:
            return PRODUCTS.pop(i)
    raise ProductNotFoundError

def buy_product(trading_book, exchange, market_data_source, console, verbosity):
    """Buy a product (product) and update trading book."""
    logger.info("Starting buy_product")
    console.print("\n[bold]Buy Product[/bold]")
    console.print("Available products:")
    for config in PRODUCTS:
        console.print(f"{config.symbol} - {config.name} (Category: {config.category})")

    # Keep asking until we get a valid symbol or user cancels
    while True:
        choice = console.input("Enter product symbol to buy (or 'q' to quit): ").upper()
        if choice.lower() == 'q':
            return
        try:
            product = next(p for p in PRODUCTS if p.symbol == choice)
            break
        except StopIteration:
            console.print("[yellow]Product not found. Please try again.[/yellow]")

    # Get quantity
    while True:
        try:
            quantity = int(console.input("Enter quantity to buy: "))
            if quantity > 0:
                break
            console.print("[yellow]Please enter a positive quantity.[/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a valid number.[/yellow]")

    # Get order type
    while True:
        order_type = console.input("Enter order type (market/limit): ").lower()
        if order_type in ['market', 'limit']:
            break
        console.print("[yellow]Please enter either 'market' or 'limit'.[/yellow]")

    limit_price = None
    if order_type == 'limit':
        while True:
            try:
                limit_price = float(console.input("Enter limit price: "))
                if limit_price > 0:
                    break
                console.print("[yellow]Please enter a positive price.[/yellow]")
            except ValueError:
                console.print("[yellow]Please enter a valid number.[/yellow]")

    try:
        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, Order.OrderSide.BUY, verbosity, limit_price=limit_price, order_type=order_type)
        logger.info(f"Bought {quantity} of {product.symbol} at {order_type} order")
        if fill.quantity > 0:
            console.print(f"[green]Bought {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        else:
            console.print(f"[yellow]Order placed for {quantity} {product.symbol} - waiting for fill[/yellow]")
        return trading_book
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return trading_book
    except Exception as e:
        logger.error(f"Unexpected error in buy_product: {str(e)}")
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        return trading_book

def sell_product(trading_book, exchange, market_data_source, console, verbosity):
    """Sell a product (product) and update trading book."""
    logger.info("Starting sell_product")
    console.print("\n[bold]Sell Product[/bold]")
    console.print("Available products:")
    for config in PRODUCTS:
        console.print(f"{config.symbol} - {config.name} (Category: {config.category})")

    # Keep asking until we get a valid symbol or user cancels
    while True:
        choice = console.input("Enter product symbol to sell (or 'q' to quit): ").upper()
        if choice.lower() == 'q':
            return
        try:
            product = next(p for p in PRODUCTS if p.symbol == choice)
            break
        except StopIteration:
            console.print("[yellow]Product not found. Please try again.[/yellow]")

    # Get quantity
    while True:
        try:
            quantity = int(console.input("Enter quantity to sell: "))
            if quantity > 0:
                break
            console.print("[yellow]Please enter a positive quantity.[/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a valid number.[/yellow]")

    # Get order type
    while True:
        order_type = console.input("Enter order type (market/limit): ").lower()
        if order_type in ['market', 'limit']:
            break
        console.print("[yellow]Please enter either 'market' or 'limit'.[/yellow]")

    limit_price = None
    if order_type == 'limit':
        while True:
            try:
                limit_price = float(console.input("Enter limit price: "))
                if limit_price > 0:
                    break
                console.print("[yellow]Please enter a positive price.[/yellow]")
            except ValueError:
                console.print("[yellow]Please enter a valid number.[/yellow]")

    try:
        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, Order.OrderSide.SELL, verbosity, limit_price=limit_price, order_type=order_type)
        logger.info(f"Sold {quantity} of {product.symbol} at {order_type} order")
        if fill.quantity > 0:
            console.print(f"[green]Sold {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        else:
            console.print(f"[yellow]Order placed for {quantity} {product.symbol} - waiting for fill[/yellow]")
        return trading_book
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return trading_book
    except Exception as e:
        logger.error(f"Unexpected error in sell_product: {str(e)}")
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        return trading_book

def _trade_product(market_data_source, exchange, trading_book, product, quantity, side: Order.OrderSide, verbosity, limit_price=None, order_type='market'):
    """Trade a product and update trading book."""
    logger.info(f"Starting _trade_product for {product} {side} {quantity} at {order_type} order")

    # Get current market data
    market_data, matches = get_market_data(market_data_source, verbosity, exchange if market_data_source == MarketDataSource.CLOB else None)
    # Process any fills that occurred
    trading_book.process_fills(matches)

    # Place order on exchange
    order_id = exchange.place_order(
        product=product.symbol,
        quantity=quantity,
        side=side,
        order_type=Order.OrderType.LIMIT if order_type == 'limit' else Order.OrderType.MARKET,
        limit_price=limit_price
    )

    logger.info(f"Placed order with order ID {order_id}")

    # Update market data and try to match immediately for better user experience
    if market_data:
        exchange.update_market_data(market_data)
        
        # For simulation mode, match orders immediately after placement
        if market_data_source == MarketDataSource.SIMULATION:
            matches = exchange.match_orders()
            trading_book.process_fills(matches)
            
            # Find any fills for our order
            for order, fill in matches:
                if order.order_id == order_id:
                    return trading_book, fill

    # If no immediate fill, create a mock fill for UI feedback
    # This will be replaced by real fills when they occur in the main loop
    from order import Fill
    fill = Fill(
        product=product.symbol,
        quantity=0,  # 0 quantity indicates no fill yet
        side=side,
        price=0.0,
        order_id=order_id
    )

    return trading_book, fill
