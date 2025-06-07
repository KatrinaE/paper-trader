import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.live import Live
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
INSTRUMENTS = {
    "EUR/USD": {"symbol": "EUR/USD", "type": "forex"},
    "XAU/USD": {"symbol": "XAU/USD", "type": "commodities"},
    "XAG/USD": {"symbol": "XAG/USD", "type": "commodities"}
}

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

def create_table(data):
    """Create a table for displaying market data"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Instrument", style="cyan")
    table.add_column("Bid", style="green")
    table.add_column("Ask", style="red")
    
    for instrument in INSTRUMENTS:
        bid = data.get(f"{instrument}_bid", "N/A")
        ask = data.get(f"{instrument}_ask", "N/A")
        table.add_row(instrument, str(bid), str(ask))
    
    return table

def update_display():
    """Update the display with current market data"""
    data = get_market_data()
    if data:
        return create_table(data)
    return None

def main():
    """Main application loop"""
    if not API_KEY:
        console.print("[red]Error: API key not found. Please set API_KEY in .env file.[/red]")
        return

    with Live(console=console, refresh_per_second=2) as live:
        while True:
            try:
                panel = update_display()
                if panel:
                    live.update(panel)
                time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[green]Exiting...[/green]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                time.sleep(1)

if __name__ == "__main__":
    main()
