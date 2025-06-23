# Standard library imports
import os
import argparse
import time
import traceback
from threading import Thread
from typing import Dict, Any

# Initialize logging
from logging_config import logger

# Configure logging
logger.info("Starting paper_trader application")

# Third-party imports
from dotenv import load_dotenv
from rich.console import Console, Group
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt
from rich.align import Align
from rich.layout import Layout
from twelvedata import TDClient
from twelvedata.endpoints import TimeSeriesEndpoint, APIUsageEndpoint

# Local imports
from products import PRODUCTS
from market_data import get_market_data
from exchange import Exchange
from trading import Order, Fill
from trading_book import TradingBook
from user_actions import add_product, remove_product, buy_product, sell_product


class RateLimiter:
    def __init__(self, max_calls, window_seconds):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []

    def wait_if_needed(self):
        # Remove old calls from the list
        now = time.time()
        self.calls = [call for call in self.calls if now - call <= self.window_seconds]

        # If we've reached the limit, wait until we can make another call
        if len(self.calls) >= self.max_calls:
            time_to_wait = self.calls[0] + self.window_seconds - now
            if time_to_wait > 0:
                console.print(f"[yellow]Rate limit reached. Waiting {time_to_wait:.1f} seconds...[/yellow]")
                time.sleep(time_to_wait)

        # Record this call
        self.calls.append(time.time())

# Load environment variables
load_dotenv()

# Initialize console
console = Console()

def create_layout(market_data, trading_book):
    """Create a layout with separate panels for Forex, Commodities, Stocks, and Trading Book"""
    # Create tables for each category with fixed column widths
    forex_table = Table(show_header=True, header_style="bold")
    forex_table.add_column("Product", style="cyan", no_wrap=True)
    forex_table.add_column("Bid", style="green", width=10)  # Fixed width for 4 digits + 2 decimal places + decimal point
    forex_table.add_column("Ask", style="red", width=10)

    commodities_table = Table(show_header=True, header_style="bold")
    commodities_table.add_column("Product", style="cyan", no_wrap=True)
    commodities_table.add_column("Bid", style="green", width=10)
    commodities_table.add_column("Ask", style="red", width=10)

    stocks_table = Table(show_header=True, header_style="bold")
    stocks_table.add_column("Product", style="cyan", no_wrap=True)
    stocks_table.add_column("Bid", style="green", width=10)
    stocks_table.add_column("Ask", style="red", width=10)

    # Add data to market tables
    for product in PRODUCTS:
        if product.category == 'forex':
            forex_table.add_row(
                product.symbol,
                str(market_data.get(f"{product.symbol}_bid", 'N/A')),
                str(market_data.get(f"{product.symbol}_ask", 'N/A'))
            )
        elif product.category == 'commodities':
            commodities_table.add_row(
                product.symbol,
                str(market_data.get(f"{product.symbol}_bid", 'N/A')),
                str(market_data.get(f"{product.symbol}_ask", 'N/A'))
            )
        elif product.category == 'stocks':
            stocks_table.add_row(
                product.symbol,
                str(market_data.get(f"{product.symbol}_bid", 'N/A')),
                str(market_data.get(f"{product.symbol}_ask", 'N/A'))
            )

    # Create trading book table
    trading_table = Table(show_header=True, header_style="bold")
    trading_table.add_column("Product", style="cyan", no_wrap=True)
    trading_table.add_column("Quantity", style="yellow")
    trading_table.add_column("Value", style="green")

    # Create controls panel
    controls_table = Table(show_header=False)
    controls_table.add_column("Menu", style="cyan", no_wrap=True)
    controls_table.add_row("- a - Add product")
    controls_table.add_row("- r - Remove product")
    controls_table.add_row("- b - Buy product")
    controls_table.add_row("- s - Sell product")
    controls_table.add_row("- q - Quit")
    controls_panel = Panel(controls_table, title="Controls", border_style="green")

    # Create orders table
    orders_table = Table(show_header=True, header_style="bold")
    orders_table.add_column("Order ID", style="cyan")
    orders_table.add_column("Product", style="cyan")
    orders_table.add_column("Side", style="yellow")
    orders_table.add_column("Type", style="green")
    orders_table.add_column("Quantity", style="yellow")
    orders_table.add_column("Limit Price", style="green")

    # Add active orders to orders table
    active_orders = trading_book.get_formatted_active_orders()
    for order in active_orders:
        orders_table.add_row(
            order["Order ID"],
            order["Product"],
            order["Side"],
            order["Type"],
            order["Quantity"],
            order["Limit Price"]
        )

    # Create panels for each table
    forex_panel = Panel(forex_table, title="Forex", border_style="green")
    commodities_panel = Panel(commodities_table, title="Commodities", border_style="green")
    stocks_panel = Panel(stocks_table, title="Stocks", border_style="green")
    trading_panel = Panel(trading_table, title="Trading Book", border_style="green")
    orders_panel = Panel(orders_table, title="Active Orders", border_style="green")

    # Create columns for each row
    top_row = Columns([forex_panel, commodities_panel], equal=True)
    middle_row = Columns([stocks_panel, trading_panel], equal=True)

    # Create controls panel
    controls_panel = Panel(Text("Controls Panel"), title="Controls", border_style="green")
    bottom_row = Columns([orders_panel, controls_panel], equal=True)

    # Add positions to trading table
    # Use the same market_data that was passed to the function
    total_value = trading_book.get_total_value(market_data)

    # Create a dictionary of current bid prices for our positions
    position_prices = {}
    for product in trading_book.positions:
        bid = market_data.get(f"{product}_bid", 0.0)
        position_prices[product] = float(bid) if bid != 'N/A' else 0.0

    for product, quantity in trading_book.positions.items():
        bid = position_prices.get(product, 0.0)
        value = quantity * bid
        trading_table.add_row(
            product,
            str(quantity),
            f"${value:.2f}"
        )

    # Add cash balance
    trading_table.add_row("Cash", "-", f"${trading_book.cash:.2f}")
    trading_table.add_row("Total Value", "-", f"${total_value:.2f}")

    # Create layout with rows
    layout = Group(
        top_row,
        middle_row,
        bottom_row
    )
    return layout

def update_display(market_data, trading_book):
    """Update the display with current market data and trading book"""
    return create_layout(market_data, trading_book)

def with_live_update(live, func, *args, **kwargs):
    """Wrapper to handle live.stop(), live.start(), and live.update() for UI actions."""
    live.stop()
    try:
        result = func(*args, **kwargs)
        if result is not None:
            live.update(result, refresh=True)
        return result
    finally:
        live.start()

def update_market_data_continuously(live, trading_book, exchange, market_data_source, verbosity):
    """Background thread to update market data every second"""
    while True:
        try:
            # Get new market data
            market_data = get_market_data(market_data_source, verbosity)
            if market_data:
                exchange.update_market_data(market_data)
                # Process fills to update cash and positions
                trading_book.process_fills()

                # Update the display
                renderable = create_layout(market_data, trading_book)
                live.update(renderable, refresh=True)
        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
        time.sleep(1)  # Update every second

def main(market_data_source='twelvedata', verbosity=1):
    """Main application loop"""
    # Initialize trading book and exchange
    trading_book = TradingBook()
    exchange = Exchange({})
    trading_book.exchange = exchange

    # Create initial layout
    market_data = get_market_data(market_data_source, verbosity)
    layout = create_layout(market_data, trading_book)

    # Create renderable from layout
    renderable = layout

    # Initialize API client if needed
    if market_data_source == 'twelvedata':
        API_KEY = os.getenv("API_KEY")
        client = TDClient(apikey=API_KEY)

    # Print header once
    console.print("Press 'b' to buy, 's' to sell, 'a' to add product, 'r' to remove product, 'q' to quit")

    # Create Live object
    live = Live(renderable, console=console, auto_refresh=False)

    # Start the market data update thread
    update_thread = Thread(target=update_market_data_continuously,
                          args=(live, trading_book, exchange, market_data_source, verbosity),
                          daemon=True)
    update_thread.start()

    # Start the Live display
    with live:
        while True:
                try:
                    # Wait for user input
                    event = input()
                except KeyboardInterrupt:
                    console.print("\n[green]Exiting...[/green]")
                    update_thread.join()
                    break

                if event.lower() == "a":
                    with_live_update(live, add_product, console)
                elif event.lower() == "r":
                    with_live_update(live, remove_product, console)
                elif event.lower() == "b":
                    trading_book = with_live_update(live, buy_product, trading_book, exchange, market_data_source, console, verbosity)
                elif event.lower() == "s":
                    trading_book = with_live_update(live, sell_product, trading_book, exchange, market_data_source, console, verbosity)
                elif event.lower() == "q":
                    console.print("\n[green]Exiting...[/green]")
                    break

if __name__ == "__main__":
    # Initialize console
    console = Console()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Paper Trader Market Data Terminal')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity level (-v for basic, -vv for detailed)')
    parser.add_argument('-m', '--market-data-source', default='twelvedata',
                        help='Market data source (twelvedata or none)')
    args = parser.parse_args()

    # Set verbosity level (0-2)
    verbosity = args.verbose + 1

    main(args.market_data_source, verbosity)
    console.print("\n[bold magenta]Market Data Terminal[/bold magenta]")
    if verbosity >= 1:
        console.print(f"[cyan]Verbosity level: {verbosity}[/cyan]")

    try:
        main(args.market_data_source, verbosity)
    except KeyboardInterrupt:
        console.print("\n[green]Exiting...[/green]")
