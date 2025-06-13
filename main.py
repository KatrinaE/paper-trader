# Standard library imports
import os
import argparse
import time
import traceback
from threading import Thread
from typing import Dict, Any

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
from rate_limiter import RateLimiter
from trading import TradingBook, Exchange, Order, Fill

# Rate limiting constants
MAX_CALLS_PER_MINUTE = 8
CALL_WINDOW_SECONDS = 60  # 1 minute

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

# Initialize API client
API_KEY = os.getenv("API_KEY")
client = TDClient(apikey=API_KEY)

# Initialize rate limiter
rate_limiter = RateLimiter(MAX_CALLS_PER_MINUTE, CALL_WINDOW_SECONDS)

# Initialize console
console = Console()

# Instruments configuration
DEFAULT_INSTRUMENTS = [
    # Forex
    {"symbol": "EUR/USD", "name": "Euro - US Dollar exchange rate", "category": "forex"},
    {"symbol": "GBP/USD", "name": "British Pound - US Dollar exchange rate", "category": "forex"},
    {"symbol": "USD/JPY", "name": "US Dollar - Japanese Yen exchange rate", "category": "forex"},

    # Commodities
    {"symbol": "XAU/USD", "name": "Gold", "category": "commodities"},
    # Silver is not in our API plan
    # {"symbol": "XAG/USD", "name": "Silver", "category": "commodities"},
    # Crude oil is not in our API plan
    # {"symbol": "CL1", "name": "Crude Oil", "category": "commodities"},

    # Stocks
    {"symbol": "AAPL", "name": "Apple Inc.", "category": "stocks"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Google)", "category": "stocks"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "category": "stocks"},
    # {"symbol": "AMZN", "name": "Amazon.com Inc.", "category": "stocks"},
    #{"symbol": "TSLA", "name": "Tesla, Inc.", "category": "stocks"}
]

INSTRUMENTS = DEFAULT_INSTRUMENTS.copy()

import random

def get_market_data(market_data_source='twelvedata', verbosity=1):
    """Fetch market data from Twelve Data API or return random prices when in none mode"""
    if market_data_source == 'none':
        # Generate random prices for all instruments
        data = {}
        for instrument in INSTRUMENTS:
            # Generate a random base price between $1 and $100
            base_price = random.uniform(1, 100)
            # Generate bid and ask prices with bid slightly lower than ask
            bid = round(base_price - random.uniform(0, 1), 2)
            ask = round(base_price + random.uniform(0, 1), 2)

            data[f"{instrument['symbol'].upper()}_bid"] = bid
            data[f"{instrument['symbol'].upper()}_ask"] = ask
        return data


    rate_limiter.wait_if_needed()
    try:
        usage_endpoint = APIUsageEndpoint(client)
        usage_data = usage_endpoint.get().as_json()


        if verbosity >= 2:
            console.print(f"API Usage: {usage_data['credits_used']}/{usage_data['credits_total']}")
            if usage_data['credits_used'] >= usage_data['credits_total']:
                console.print("[red]WARNING: API credits are exhausted[/red]")

            console.print(
                f"[cyan]Current API credit usage: {usage_data.get('current_usage', 'N/A')}/{usage_data.get('plan_limit', 'N/A')}" + \
                    f"; Daily API credit usage: {usage_data.get('daily_usage', 'N/A')}/{usage_data.get('plan_daily_limit', 'N/A')} [/cyan]")
            if usage_data.get('current_usage', 0) >= usage_data.get('plan_limit', 0) or \
                usage_data.get('daily_usage', 0) >= usage_data.get('plan_daily_limit', 0):
                console.print("[red]No credits remaining! Please upgrade your plan or wait for credits to reset.[/red]")
                return {}

        # Fetch market data for each instrument
        data = {}
        for instrument in INSTRUMENTS:
            ts_endpoint = TimeSeriesEndpoint(client)
            ts_endpoint.init(
                symbol=instrument['symbol'],
                interval="1min",
                outputsize=1,
                timezone="UTC"
            )

            try:
                df = ts_endpoint.get().as_json()
                if len(df) > 0:
                    data[f"{instrument['symbol'].upper()}_bid"] = float(df[0]['high'])
                    data[f"{instrument['symbol'].upper()}_ask"] = float(df[0]['low'])
                else:
                    data[f"{instrument['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{instrument['symbol'].upper()}_ask"] = 'N/A'
            except Exception as e:
                if verbosity >= 1:
                    console.print(f"Error fetching {instrument['symbol']}: {str(e)}")
                    data[f"{instrument['symbol'].upper()}_bid"] = 'N/A'
                    data[f"{instrument['symbol'].upper()}_ask"] = 'N/A'

        return data
    except Exception as e:
        console.print(f"Error fetching data: {str(e)}")
        console.print(f"Full error details: {traceback.format_exc()}")
        return {}

def create_layout(data, trading_book):
    """Create a layout with separate panels for Forex, Commodities, Stocks, and Trading Book"""
    # Create tables for each category
    forex_table = Table(show_header=True, header_style="bold")
    forex_table.add_column("Instrument", style="cyan", no_wrap=True)
    forex_table.add_column("Bid", style="green")
    forex_table.add_column("Ask", style="red")

    commodities_table = Table(show_header=True, header_style="bold")
    commodities_table.add_column("Instrument", style="cyan", no_wrap=True)
    commodities_table.add_column("Bid", style="green")
    commodities_table.add_column("Ask", style="red")

    stocks_table = Table(show_header=True, header_style="bold")
    stocks_table.add_column("Instrument", style="cyan", no_wrap=True)
    stocks_table.add_column("Bid", style="green")
    stocks_table.add_column("Ask", style="red")

    # Add data to market tables
    for config in INSTRUMENTS:
        if config['category'] == 'forex':
            forex_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )
        elif config['category'] == 'commodities':
            commodities_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )
        elif config['category'] == 'stocks':
            stocks_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )

    # Create trading book table
    trading_table = Table(show_header=True, header_style="bold")
    trading_table.add_column("Product", style="cyan", no_wrap=True)
    trading_table.add_column("Quantity", style="yellow")
    trading_table.add_column("Value", style="green")

    # Add positions to trading table
    market_data = {}
    for product in trading_book.positions:
        bid = data.get(f"{product}_bid", 'N/A')
        if bid != 'N/A':
            market_data[product] = float(bid)

    total_value = trading_book.get_total_value(market_data)

    for product, quantity in trading_book.positions.items():
        bid = market_data.get(product, 0.0)
        value = quantity * bid
        trading_table.add_row(
            product,
            str(quantity),
            f"${value:.2f}"
        )

    # Add cash balance
    trading_table.add_row("Cash", "-", f"${trading_book.cash:.2f}")
    trading_table.add_row("Total Value", "-", f"${total_value:.2f}")

    # Create controls panel
    controls_table = Table(show_header=False)
    controls_table.add_column("Menu", style="cyan", no_wrap=True)
    controls_table.add_row("- a - Add instrument")
    controls_table.add_row("- r - Remove instrument")
    controls_table.add_row("- b - Buy product")
    controls_table.add_row("- s - Sell product")
    controls_table.add_row("- q - Quit")
    controls_panel = Panel(controls_table, title="Controls", border_style="green")

    # Create panels for each table
    forex_panel = Panel(forex_table, title="Forex", border_style="green")
    commodities_panel = Panel(commodities_table, title="Commodities", border_style="green")
    stocks_panel = Panel(stocks_table, title="Stocks", border_style="green")
    trading_panel = Panel(trading_table, title="Trading Book", border_style="green")

    # Create columns for each row
    top_row = Columns([forex_panel, commodities_panel], equal=True)
    bottom_row = Columns([stocks_panel, trading_panel], equal=True)

    # Create the final layout with three rows
    return Group(top_row, bottom_row, controls_panel)

    # Add data to market tables
    for config in INSTRUMENTS:
        if config['category'] == 'forex':
            forex_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )
        elif config['category'] == 'commodities':
            commodities_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )
        elif config['category'] == 'stocks':
            stocks_table.add_row(
                config['symbol'],
                str(data.get(f"{config['symbol']}_bid", 'N/A')),
                str(data.get(f"{config['symbol']}_ask", 'N/A'))
            )

    # Create panels for each table
    forex_panel = Panel(forex_table, title="Forex", border_style="cyan")
    commodities_panel = Panel(commodities_table, title="Commodities", border_style="yellow")
    stocks_panel = Panel(stocks_table, title="Stocks", border_style="magenta")
    trading_panel = Panel(trading_table, title="Trading Book", border_style="green")

    # Create columns for each row
    top_row = Columns([forex_panel, commodities_panel], equal=True)
    bottom_row = Columns([stocks_panel, trading_panel], equal=True)

    # Create the final layout with two rows
    return Group(top_row, bottom_row)

def update_display(data, trading_book):
    """Update the display with current market data and trading book"""
    return create_layout(data, trading_book)

def add_instrument(live):
    """Add a new instrument"""
    # Temporarily stop the main Live display
    live.stop()
    try:
        console.print("\n[bold]Add Instrument[/bold]")
        symbol = console.input("Enter symbol (e.g. EUR/USD): ")
        name = console.input("Enter name/description: ")

        # Loop until we get a valid category
        while True:
            category = console.input("Enter category (forex/commodities/stocks): ").lower()
            if category in ["forex", "commodities", "stocks"]:
                break
            console.print("[yellow]Oops! Please enter either 'forex', 'commodities', or 'stocks'.[/yellow]")

        INSTRUMENTS.append({"symbol": symbol, "name": name, "category": category})
        console.print(f"[green]Added {symbol} - {name} (Category: {category})[/green]")
    finally:
        # Restart the main Live display
        live.start()

def remove_instrument(live):
    """Remove an existing instrument"""
    # Temporarily stop the main Live display
    live.stop()
    try:
        console.print("\n[bold]Remove Instrument[/bold]")
        console.print("Available instruments:")
        for config in INSTRUMENTS:
            console.print(f"{config['symbol']} - {config['name']} (Category: {config['category']})")

        # Keep asking until we get a valid symbol or user cancels
        while True:
            choice = console.input("Enter symbol to remove (or 'q' to cancel): ")
            if choice.lower() == 'q':
                return

            # Find the instrument by symbol
            for i, config in enumerate(INSTRUMENTS):
                if config['symbol'] == choice:
                    removed_config = INSTRUMENTS.pop(i)
                    console.print(f"[green]Removed {removed_config['symbol']} - {removed_config['name']} (Category: {removed_config['category']})[/green]")
                    return

            console.print("[yellow]Invalid symbol. Please try again or enter 'q' to cancel.[/yellow]")
    finally:
        # Restart the main Live display
        live.start()

def main(market_data_source='twelvedata', verbosity=1):
    """Main application loop"""
    # Initialize trading book and exchange
    trading_book = TradingBook()
    exchange = Exchange({})

    # Create initial layout
    data = get_market_data(market_data_source, verbosity)
    layout = create_layout(data, trading_book)

    # Create a single renderable that we'll update
    renderable = layout

    # Print header once
    console.print("Press 'b' to buy, 's' to sell, 'a' to add instrument, 'r' to remove instrument, 'q' to quit")

    with Live(renderable, console=console, auto_refresh=False) as live:
        while True:
            try:
                # Wait for user input
                event = Prompt.ask("\n")

                if event.lower() == "a":
                    # First add the instrument
                    add_instrument(live)

                    # Create a new layout with updated data
                    new_layout = update_display(get_market_data(market_data_source, verbosity), trading_book)
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "r":
                    # First remove the instrument
                    remove_instrument(live)

                    # Create a new layout with updated data
                    new_layout = update_display(get_market_data(market_data_source, verbosity), trading_book)
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "b":
                    # Buy product
                    product = Prompt.ask("Enter product symbol to buy")
                    quantity = int(Prompt.ask("Enter quantity to buy"))

                    try:
                        # Get current market data
                        data = get_market_data(market_data_source, verbosity)
                        exchange.update_market_data(data)

                        # Create and execute order
                        order = Order(product, quantity, 'buy')
                        fill = exchange.execute_order(order)

                        # Update trading book
                        trading_book.cash -= fill.quantity * fill.price
                        trading_book.add_to_position(fill.product, fill.quantity)
                        trading_book.history.append(fill)

                        console.print(f"[green]Bought {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")

                        # Update layout with new data and trading book
                        new_layout = update_display(data, trading_book)
                        if new_layout:
                            renderable = new_layout
                            live.update(renderable, refresh=True)
                    except Exception as e:
                        console.print(f"[red]Error buying: {str(e)}[/red]")
                elif event.lower() == "s":
                    # Sell product
                    product = Prompt.ask("Enter product symbol to sell")
                    quantity = int(Prompt.ask("Enter quantity to sell"))

                    try:
                        # Get current market data
                        data = get_market_data(market_data_source, verbosity)
                        exchange.update_market_data(data)

                        # Create and execute order
                        order = Order(product, quantity, 'sell')
                        fill = exchange.execute_order(order)

                        # Update trading book
                        trading_book.cash += fill.quantity * fill.price
                        trading_book.remove_from_position(fill.product, fill.quantity)
                        trading_book.history.append(fill)

                        console.print(f"[green]Sold {fill.quantity} of {fill.product} at ${fill.price:.2f}[/green]")

                        # Update layout with new data and trading book
                        new_layout = update_display(data, trading_book)
                        if new_layout:
                            renderable = new_layout
                            live.update(renderable, refresh=True)
                    except Exception as e:
                        console.print(f"[red]Error selling: {str(e)}[/red]")
                elif event.lower() == "q":
                    console.print("\n[green]Exiting...[/green]")
                    break

                # Update the existing layout with new data
                data = get_market_data(market_data_source, verbosity)
                if data:
                    exchange.update_market_data(data)
                    renderable = create_layout(data, trading_book)
                    live.update(renderable, refresh=True)

            except KeyboardInterrupt:
                console.print("\n[green]Exiting...[/green]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                time.sleep(1)

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
