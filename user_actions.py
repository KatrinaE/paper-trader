import logging
from rich.prompt import Prompt

from products import PRODUCTS

# Configure user actions logger
logger = logging.getLogger('user_actions')
from market_data import get_market_data
from exchange import Exchange
from trading import Order, Fill
from trading_book import TradingBook
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
    PRODUCTS.append({"symbol": symbol, "name": name, "category": category})

def remove_product(console):
    """Remove an existing product."""
    logger.info("Starting remove_product")
    console.print("\n[bold]Remove Product[/bold]")
    """Remove an existing product."""
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
        if config['symbol'] == choice:
            return PRODUCTS.pop(i)
    raise ProductNotFoundError

def buy_product(trading_book, exchange, market_data_source, console, verbosity):
    """Buy a product (product) and update trading book."""
    logger.info("Starting buy_product")
    product = Prompt.ask("Enter product symbol to buy")
    quantity = int(Prompt.ask("Enter quantity to buy"))
    try:
        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, BUY, verbosity)
        console.print(f"[green]Bought {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        return trading_book
    except Exception as e:
        console.print(f"[red]Error buying: {str(e)}[/red]")

def sell_product(trading_book, exchange, market_data_source, console, verbosity):
    """Sell a product (product) and update trading book."""
    logger.info("Starting sell_product")
    """Sell a product (product) and update trading book."""
    product = Prompt.ask("Enter product symbol to sell")
    quantity = int(Prompt.ask("Enter quantity to sell"))
    try:
        trading_book, fill = _trade_product(market_data_source, exchange, trading_book, product, quantity, SELL, verbosity)
        console.print(f"[green]Sold {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        return trading_book
    except Exception as e:
        console.print(f"[red]Error selling: {str(e)}[/red]")

def _trade_product(market_data_source, exchange, trading_book, product, quantity, side, verbosity):
     # Get current market data
    market_data = get_market_data(market_data_source, verbosity)
    exchange.update_market_data(market_data)

    # Create and execute order
    order = Order(product, quantity, side)
    fill = exchange.execute_order(order)

    # Update trading book
    if side == BUY:
        trading_book.cash -= fill.quantity * fill.price
        trading_book.add_to_position(fill.product, fill.quantity)
    elif side == SELL:
        trading_book.cash += fill.quantity * fill.price
        trading_book.remove_from_position(fill.product, fill.quantity)
    trading_book.history.append(fill)
    return trading_book, fill