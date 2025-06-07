import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
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
DEFAULT_INSTRUMENTS = {
    "EUR/USD": {"symbol": "EUR/USD", "name": "Euro - US Dollar exchange rate"},
    "XAU/USD": {"symbol": "XAU/USD", "name": "Gold"},
    "XAG/USD": {"symbol": "XAG/USD", "name": "Silver"}
}

INSTRUMENTS = DEFAULT_INSTRUMENTS.copy()

def get_market_data():
    """Fetch market data from Twelve Data API"""
    try:
        console.print("[yellow]Fetching market data...[/yellow]")
        data = {}
        
        # Fetch data for each instrument
        for instrument, config in INSTRUMENTS.items():
            console.print(f"[yellow]Fetching data for {instrument}...[/yellow]")
            
            # Get real-time quote
            quote = client.quote(
                symbol=config["symbol"],
                interval="1min"
            )
            
            if quote:
                console.print(f"[green]Received data for {instrument}[/green]")
                # Extract bid/ask prices
                bid = getattr(quote, "bid", "N/A")
                ask = getattr(quote, "ask", "N/A")
                
                # Store in data dictionary
                data[f"{instrument}_bid"] = bid
                data[f"{instrument}_ask"] = ask
            else:
                console.print(f"[red]No quote data received for {instrument}[/red]")
        
        if not data:
            console.print("[red]No market data received from API[/red]")
        
        return data
    except Exception as e:
        console.print(f"[red]Error fetching data: {str(e)}[/red]")
        console.print(f"[red]Full error: {str(e)}[/red]")  # Print full error for debugging
        return None

def create_menu():
    """Create a menu panel"""
    menu = """
[bold]Menu:[/bold]
- [yellow]a[/yellow] - Add instrument
- [yellow]r[/yellow] - Remove instrument
- [yellow]q[/yellow] - Quit
    """
    return Panel(menu, title="[bold magenta]Controls[/bold magenta]", border_style="blue")

def create_table(data):
    """Create a table for displaying market data"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Instrument", style="cyan")
    table.add_column("Bid", style="green")
    table.add_column("Ask", style="red")
    
    # Add empty row if no data
    if not data:
        table.add_row("No data available", "N/A", "N/A")
    else:
        for instrument in INSTRUMENTS:
            bid = data.get(f"{instrument}_bid", "N/A")
            ask = data.get(f"{instrument}_ask", "N/A")
            table.add_row(instrument, str(bid), str(ask))
    
    return table

def create_layout(data):
    """Create the full layout with market data and menu"""
    market_table = create_table(data)
    menu = create_menu()
    
    # Create a layout with two columns
    layout = Table.grid(expand=True)
    layout.add_column("market", min_width=60)
    layout.add_column("controls", min_width=20)
    layout.add_row(market_table, menu)
    
    # Store the market table and menu for later updates
    layout.market_table = market_table
    layout.menu = menu
    
    return layout

def update_layout(layout, data):
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
        INSTRUMENTS[symbol] = {"symbol": symbol, "name": name}
        console.print(f"[green]Added {symbol} - {name}[/green]")
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
        for symbol, config in INSTRUMENTS.items():
            console.print(f"{symbol} - {config['name']}")
        
        choice = console.input("Enter symbol to remove (or 'q' to cancel): ")
        if choice.lower() == 'q':
            return
        
        if choice in INSTRUMENTS:
            del INSTRUMENTS[choice]
            console.print(f"[green]Removed {choice}[/green]")
        else:
            console.print("[red]Invalid symbol[/red]")
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
    
    with Live(renderable, console=console, refresh_per_second=2, auto_refresh=False) as live:
        while True:
            try:
                # Wait for user input
                event = Prompt.ask("\nPress a key (a/r/q)")
                
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
                    new_layout = create_layout(data)
                    if new_layout:
                        renderable = new_layout
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
