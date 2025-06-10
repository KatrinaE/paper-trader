import os
from dotenv import load_dotenv
from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt
import time
from twelvedata import TDClient
import argparse

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

def get_market_data(verbosity=1):
    """Fetch market data from Twelve Data API with rate limiting"""

    rate_limiter.wait_if_needed()

    try:
        # Check credit usage first
        client = TDClient(apikey=API_KEY)
        credit_usage = client.api_usage()
        if credit_usage:
            usage_data = credit_usage.as_json()
            console.print(
                f"[cyan]Current credit usage: {usage_data.get('current_usage', 'N/A')}/{usage_data.get('plan_limit', 'N/A')}" + \
                    f";Daily usage: {usage_data.get('daily_usage', 'N/A')}/{usage_data.get('plan_daily_limit', 'N/A')} [/cyan]")
            if usage_data.get('current_usage', 0) >= usage_data.get('plan_limit', 0) or \
                usage_data.get('daily_usage', 0) >= usage_data.get('plan_daily_limit', 0):
                console.print("[red]No credits remaining! Please upgrade your plan or wait for credits to reset.[/red]")
                return {}

        data = {}
        
        # Fetch data for each instrument
        for instrument in INSTRUMENTS:
            # Wait if we've hit the rate limit
            rate_limiter.wait_if_needed()

            if verbosity >= 2:
                console.print(f"[yellow]Fetching data for {instrument['symbol']}...[/yellow]")

            # Get time series data
            try:
                ts = client.time_series(
                    symbol=instrument["symbol"],
                    interval="1min",
                    outputsize=1
                )
                
                if ts:
                    json_data = ts.as_json()
                    if isinstance(json_data, tuple) and len(json_data) > 0:
                        if verbosity >= 2:
                            console.print(f"[green]Received data for {instrument['symbol']}[/green]")
                        # Extract last price as bid/ask (for simplicity)
                        last_price = json_data[0]["close"]
                        
                        # Store in data dictionary
                        data[f"{instrument['symbol']}_bid"] = last_price
                        data[f"{instrument['symbol']}_ask"] = last_price
                    else:
                        console.print(f"[red]No data points received for {instrument['symbol']}[/red]")
                else:
                    console.print(f"[red]No time series object received for {instrument['symbol']}[/red]")
            except Exception as e:
                console.print(f"[red]Error fetching data for {instrument['symbol']}: {str(e)}[/red]")
                import traceback
                console.print(f"[red]Full error details: {traceback.format_exc()}[/red]")

        if not data:
            console.print("[red]No market data received from API[/red]")
        else:
            if verbosity >= 2:
                console.print("[green]Successfully fetched market data[/green]")
        
        return data
    except Exception as e:
        console.print(f"[red]Error fetching data: {str(e)}[/red]")
        import traceback
        console.print(f"[red]Full error details: {traceback.format_exc()}[/red]")
        return {}

def create_layout(data):
    """Create a layout with separate panels for Forex, Commodities, and Stocks"""
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

    controls_table = Table(show_header=False)
    controls_table.add_column("Menu", style="cyan", no_wrap=True)
    controls_table.add_row("- a - Add instrument")
    controls_table.add_row("- r - Remove instrument")
    controls_table.add_row("- q - Quit")

    # Add data to tables
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

    # Create controls panel
    controls_table = Table(show_header=False)
    controls_table.add_column("Menu", style="cyan", no_wrap=True)
    controls_table.add_row("- a - Add instrument")
    controls_table.add_row("- r - Remove instrument")
    controls_table.add_row("- q - Quit")
    controls_panel = Panel(controls_table, title="Controls", border_style="green")

    # Create columns for each row
    top_row = Columns([forex_panel, commodities_panel], equal=True)
    bottom_row = Columns([stocks_panel, controls_panel], equal=True)

    # Create the final layout with two rows
    return Group(top_row, bottom_row)

def update_display(data):
    """Update the display with current market data"""
    return create_layout(data)

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

def main(verbosity=1):
    """Main application loop"""
    if not API_KEY:
        console.print("[red]Error: API key not found. Please set API_KEY in .env file.[/red]")
        return

    # Create initial layout
    data = get_market_data(verbosity)
    layout = create_layout(data)
    
    # Create a single renderable that we'll update
    renderable = layout
    
    # Print header once
    console.print("\nMarket Data Terminal")
    console.print("Press 'a' to add instrument, 'r' to remove, 'q' to quit")
    
    with Live(renderable, console=console, auto_refresh=False) as live:
        while True:
            try:
                # Wait for user input
                event = Prompt.ask("\n")
                
                if event.lower() == "a":
                    # First add the instrument
                    add_instrument(live)
                    
                    # Create a new layout with updated data
                    new_layout = update_display(get_market_data(verbosity))
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "r":
                    # First remove the instrument
                    remove_instrument(live)
                    
                    # Create a new layout with updated data
                    new_layout = update_display(get_market_data(verbosity))
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "q":
                    console.print("\n[green]Exiting...[/green]")
                    break
                
                # Update the existing layout with new data
                data = get_market_data(verbosity)
                if data:
                    console.print("[green]Got market data... updating layout[/green]")
                    renderable = create_layout(data)
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
    args = parser.parse_args()
    
    # Set verbosity level (0-2)
    verbosity = min(args.verbose, 2)
    
    # Print welcome message with verbosity level
    console.print("\n[bold magenta]Market Data Terminal[/bold magenta]")
    console.print("Press 'a' to add instrument, 'r' to remove, 'q' to quit")
    if verbosity >= 1:
        console.print(f"[cyan]Verbosity level: {verbosity}[/cyan]")
    
    try:
        main(verbosity)
    except KeyboardInterrupt:
        console.print("\n[green]Exiting...[/green]")
