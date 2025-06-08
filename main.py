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

# Load environment variables
load_dotenv()

# Initialize console
console = Console()

# Configuration
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    console.print("[red]Error: API key not found. Please set API_KEY in .env file.[/red]")
    exit(1)

# Initialize Twelve Data client
client = TDClient(apikey=API_KEY)

# Instruments configuration
DEFAULT_INSTRUMENTS = [
    # Forex
    {"symbol": "EUR/USD", "name": "Euro - US Dollar exchange rate", "category": "forex"},
    {"symbol": "GBP/USD", "name": "British Pound - US Dollar exchange rate", "category": "forex"},
    {"symbol": "USD/JPY", "name": "US Dollar - Japanese Yen exchange rate", "category": "forex"},
    
    # Commodities
    {"symbol": "XAU/USD", "name": "Gold", "category": "commodities"},
    {"symbol": "XAG/USD", "name": "Silver", "category": "commodities"},
    {"symbol": "CL/USD", "name": "Crude Oil", "category": "commodities"},
    
    # Stocks
    {"symbol": "AAPL", "name": "Apple Inc.", "category": "stocks"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Google)", "category": "stocks"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "category": "stocks"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "category": "stocks"},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "category": "stocks"}
]

INSTRUMENTS = DEFAULT_INSTRUMENTS.copy()

def get_market_data():
    """Fetch market data from Twelve Data API"""
    try:
        console.print("[yellow]Fetching market data...[/yellow]")
        data = {}
        
        # Fetch data for each instrument
        for instrument in INSTRUMENTS:
            console.print(f"[yellow]Fetching data for {instrument['symbol']}...[/yellow]")
            
            # Get real-time quote
            quote = client.quote(
                symbol=instrument["symbol"],
                interval="1min"
            )
            
            if quote:
                console.print(f"[green]Received data for {instrument['symbol']}[/green]")
                # Extract bid/ask prices
                bid = getattr(quote, "bid", "N/A")
                ask = getattr(quote, "ask", "N/A")
                
                # Store in data dictionary
                data[f"{instrument['symbol']}_bid"] = bid
                data[f"{instrument['symbol']}_ask"] = ask
            else:
                console.print(f"[red]No quote data received for {instrument['symbol']}[/red]")
        
        if not data:
            console.print("[red]No market data received from API[/red]")
        
        return data
    except Exception as e:
        console.print(f"[red]Error fetching data: {str(e)}[/red]")
        console.print(f"[red]Full error: {str(e)}[/red]")  # Print full error for debugging
        return None

def create_layout(data):
    """Create a layout with separate panels for Forex, Commodities, and Stocks"""
    # Create tables for each category
    forex_table = Table(title="Forex", show_header=True, header_style="bold")
    forex_table.add_column("Instrument", style="cyan", no_wrap=True)
    forex_table.add_column("Bid", style="green")
    forex_table.add_column("Ask", style="red")

    commodities_table = Table(title="Commodities", show_header=True, header_style="bold")
    commodities_table.add_column("Instrument", style="cyan", no_wrap=True)
    commodities_table.add_column("Bid", style="green")
    commodities_table.add_column("Ask", style="red")

    stocks_table = Table(title="Stocks", show_header=True, header_style="bold")
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
    controls_panel = Panel(controls_table, title="Controls", border_style="green")

    # Create columns for each row
    top_row = Columns([forex_panel, commodities_panel], equal=True)
    bottom_row = Columns([stocks_panel, controls_panel], equal=True)

    # Create the final layout with two rows
    return Group(top_row, bottom_row)

    # Create tables for each category
    forex_table = Table(title="Forex", show_header=True, header_style="bold")
    forex_table.add_column("Instrument", style="cyan", no_wrap=True)
    forex_table.add_column("Bid", style="green")
    forex_table.add_column("Ask", style="red")

    commodities_table = Table(title="Commodities", show_header=True, header_style="bold")
    commodities_table.add_column("Instrument", style="cyan", no_wrap=True)
    commodities_table.add_column("Bid", style="green")
    commodities_table.add_column("Ask", style="red")

    stocks_table = Table(title="Stocks", show_header=True, header_style="bold")
    stocks_table.add_column("Instrument", style="cyan", no_wrap=True)
    stocks_table.add_column("Bid", style="green")
    stocks_table.add_column("Ask", style="red")

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

    # Create panels for each category
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

    # Add panels to layout
    layout["forex"].update(forex_panel)
    layout["commodities"].update(commodities_panel)
    layout["stocks"].update(stocks_panel)
    layout["controls"].update(controls_panel)

    return layout

def create_menu():
    """Create a menu panel"""
    menu = """
[bold]Menu:[/bold]
- [yellow]a[/yellow] - Add instrument
- [yellow]r[/yellow] - Remove instrument
- [yellow]q[/yellow] - Quit
    """
    return Panel(menu, title="[bold magenta]Controls[/bold magenta]", border_style="blue")

    """Update the existing layout with new data"""
    # Update the market table
    layout.market_table.rows.clear()
    
    # Add empty row if no data
    if not data:
        layout.market_table.add_row("No data available", "N/A", "N/A")
    else:
        for instrument in INSTRUMENTS:
            bid = data.get(f"{instrument}_bid", "N/A")
            ask = data.get(f"{instrument}_ask", "N/A")
            layout.market_table.add_row(instrument, str(bid), str(ask))
    
    return layout

def update_display():
    """Update the display with current market data"""
    data = get_market_data()
    if data:
        return create_table(data)
    return None

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
            category = console.input("Enter category (forex/commodities): ").lower()
            if category in ["forex", "commodities"]:
                break
            console.print("[yellow]Oops! Please enter either 'forex' or 'commodities'.[/yellow]")
        
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

def main():
    """Main application loop"""
    if not API_KEY:
        console.print("[red]Error: API key not found. Please set API_KEY in .env file.[/red]")
        return

    # Create initial layout
    layout = create_layout(get_market_data())
    
    # Create a single renderable that we'll update
    renderable = layout
    
    # Print header once
    console.print("\nMarket Data Terminal")
    console.print("Press 'a' to add instrument, 'r' to remove, 'q' to quit")
    
    with Live(renderable, console=console, refresh_per_second=2, auto_refresh=False) as live:
        while True:
            try:
                # Wait for user input
                event = Prompt.ask("\n")
                
                if event.lower() == "a":
                    # First add the instrument
                    add_instrument(live)
                    
                    # Create a new layout with updated data
                    new_layout = create_layout(get_market_data())
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "r":
                    # First remove the instrument
                    remove_instrument(live)
                    
                    # Create a new layout with updated data
                    new_layout = create_layout(get_market_data())
                    if new_layout:
                        renderable = new_layout
                        live.update(renderable, refresh=True)
                elif event.lower() == "q":
                    console.print("\n[green]Exiting...[/green]")
                    break
                
                # Update the existing layout with new data
                data = get_market_data()
                if data:
                    renderable = create_layout(data)
                    live.update(renderable, refresh=True)
                
            except KeyboardInterrupt:
                console.print("\n[green]Exiting...[/green]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                time.sleep(1)

if __name__ == "__main__":
    console = Console()
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    client = TDClient(apikey=API_KEY)
    
    # Print welcome message
    console.print("\n[bold magenta]Market Data Terminal[/bold magenta]")
    console.print("Press 'a' to add instrument, 'r' to remove, 'q' to quit")
    
    main()
