from rich.prompt import Prompt

from instruments import INSTRUMENTS
from market_data import get_market_data
from trading import TradingBook, Exchange, Order, Fill

def add_instrument(console):
    """Add a new instrument."""
    console.print("\n[bold]Add Instrument[/bold]")
    symbol = console.input("Enter symbol (e.g. EUR/USD): ")
    name = console.input("Enter name/description: ")

    # Loop until we get a valid category
    while True:
        category = console.input("Enter category (forex/commodities/stocks): ").lower()
        if category in ["forex", "commodities", "stocks"]:
            break
        console.print("[yellow]Oops! Please enter either 'forex', 'commodities', or 'stocks'.[/yellow]")

    _add_instrument(symbol, name, category)
    console.print(f"[green]Added {symbol} - {name} (Category: {category})[/green]")
    # No need to return a layout

def _add_instrument(symbol, name, category):
    INSTRUMENTS.append({"symbol": symbol, "name": name, "category": category})

def remove_instrument(console):
    """Remove an existing instrument."""
    console.print("\n[bold]Remove Instrument[/bold]")
    console.print("Available instruments:")
    for config in INSTRUMENTS:
        console.print(f"{config['symbol']} - {config['name']} (Category: {config['category']})")

    # Keep asking until we get a valid symbol or user cancels
    while True:
        choice = console.input("Enter symbol to remove (or 'q' to cancel): ")
        if choice.lower() == 'q':
            return None

        try:
            removed_config = _remove_instrument(choice)
            console.print(f"[green]Removed {removed_config['symbol']} - {removed_config['name']} (Category: {removed_config['category']})[/green]")
            return None
        except ProductNotFoundError:
            console.print("[yellow]Invalid symbol. Please try again or enter 'q' to cancel.[/yellow]")

class ProductNotFoundError:
    pass

def _remove_instrument(choice):
    for i, config in enumerate(INSTRUMENTS):
        if config['symbol'] == choice:
            return INSTRUMENTS.pop(i)
    raise ProductNotFoundError

def buy_instrument(trading_book, exchange, market_data_source, console, verbosity):
    """Buy a product (instrument) and update trading book."""
    product = Prompt.ask("Enter product symbol to buy")
    quantity = int(Prompt.ask("Enter quantity to buy"))
    try:
        trading_book, fill = _buy_instrument(market_data_source, exchange, trading_book, product, quantity, verbosity)
        console.print(f"[green]Bought {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        return trading_book
    except Exception as e:
        console.print(f"[red]Error buying: {str(e)}[/red]")

def _buy_instrument(market_data_source, exchange, trading_book, product, quantity, verbosity):
     # Get current market data
    market_data = get_market_data(market_data_source, verbosity)
    exchange.update_market_data(market_data)

    # Create and execute order
    order = Order(product, quantity, 'buy')
    fill = exchange.execute_order(order)

    # Update trading book
    trading_book.cash -= fill.quantity * fill.price
    trading_book.add_to_position(fill.product, fill.quantity)
    trading_book.history.append(fill)
    return trading_book, fill

def sell_instrument(trading_book, exchange, market_data_source, console, verbosity):
    """Sell a product (instrument) and update trading book."""
    product = Prompt.ask("Enter product symbol to sell")
    quantity = int(Prompt.ask("Enter quantity to sell"))
    try:
        trading_book, fill = _sell_instrument(market_data_source, exchange, trading_book, product, quantity, verbosity)
        console.print(f"[green]Sold {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")
        return trading_book
    except Exception as e:
        console.print(f"[red]Error selling: {str(e)}[/red]")

def _sell_instrument(market_data_source, exchange, trading_book, product, quantity, verbosity):
    # Get current market data
    market_data = get_market_data(market_data_source, verbosity)
    exchange.update_market_data(market_data)

    # Create and execute order
    order = Order(product, quantity, 'sell')
    fill = exchange.execute_order(order)

    # Update trading book
    trading_book.cash += fill.quantity * fill.price
    trading_book.remove_from_position(fill.product, fill.quantity)
    trading_book.history.append(fill)
    return trading_book, fill