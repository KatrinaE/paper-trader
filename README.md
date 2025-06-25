# Paper Trader

A terminal-based paper trading application that simulates real trading with live market data. Practice trading forex, commodities, and stocks without risking real money.

## Features
- **Real-time Market Data**: Live prices from Twelve Data API with fallback simulation mode
- **Order Management**: Place market and limit orders with realistic order matching
- **Portfolio Tracking**: Monitor positions, cash balance, and total portfolio value
- **Multi-Asset Trading**: Trade forex (EUR/USD, GBP/USD, USD/JPY), commodities (Gold), and stocks (AAPL, GOOGL, MSFT)
- **Rich Terminal UI**: Clean, interactive interface with live updates
- **Comprehensive Logging**: Track all trades and market activity

## Setup

### Prerequisites
- Python 3.9 or higher
- Terminal with color support for best experience

### Installation
1. **Get a free API key from Twelve Data** (optional for live data):
   - Visit https://twelvedata.com/
   - Sign up for an account
   - Create an API key in your dashboard

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (optional):
```bash
# Create .env file with your API key for live data
echo "TWELVEDATA_API_KEY=your_api_key_here" > .env
```

4. **Run the application**:
```bash
python main.py                    # Run with live data (requires API key)
python main.py -m simulation      # Run with simulated data (no API key needed)
python main.py -v                 # Run with verbose logging
```

## How to Use

### Getting Started
1. **Launch the application** using one of the run commands above
2. **View the dashboard** showing:
   - Current market prices (bid/ask) for all instruments
   - Your portfolio summary (cash, positions, total value)
   - Active orders
   - Recent fills

### Trading Commands
Use these commands in the application:

- **`buy [symbol] [quantity] [price]`** - Place a buy order
  - `buy EUR/USD 1000` (market order)
  - `buy AAPL 10 190.00` (limit order)

- **`sell [symbol] [quantity] [price]`** - Place a sell order
  - `sell XAU/USD 1` (market order)
  - `sell GOOGL 5 180.00` (limit order)

- **`add [symbol]`** - Add a new product to track
- **`remove [symbol]`** - Remove a product from tracking
- **`quit`** or **`exit`** - Exit the application

### Available Instruments
- **Forex**: EUR/USD, GBP/USD, USD/JPY
- **Commodities**: XAU/USD (Gold)
- **Stocks**: AAPL, GOOGL, MSFT

*Note: You start with $10,000 in cash to begin trading.*

## Key Abstractions

### Core Components

**Order System** (`order.py`)
- `Order` class: Represents buy/sell orders with market/limit types
- `Fill` class: Represents completed order executions
- Handles order lifecycle from placement to completion

**Exchange** (`exchange.py`)
- Central order book managing all trading activity
- Matches incoming orders against current market prices
- Maintains order state and generates fills
- Implements realistic order matching logic

**Trading Book** (`trading_book.py`)
- Portfolio manager tracking cash, positions, and total value
- Processes fills and updates account balances
- Maintains trading history and active orders
- Calculates profit/loss and portfolio metrics

**Market Data** (`market_data.py`)
- Real-time price feed from Twelve Data API
- Simulation mode with realistic price movements
- Bid/ask spread management
- Rate limiting for API compliance

**Products** (`products.py`)
- Financial instrument definitions
- Symbol, name, category, and initial price configuration
- Extensible product catalog system

## Important Files

### Core Application Files
- **`main.py`** - Application entry point and Rich-based UI
- **`exchange.py`** - Order book and matching engine
- **`trading_book.py`** - Portfolio and position management
- **`order.py`** - Order and Fill data structures
- **`market_data.py`** - Real-time and simulated market data
- **`user_actions.py`** - Command parsing and validation
- **`products.py`** - Financial instrument definitions

### Configuration & Support
- **`requirements.txt`** - Python dependencies
- **`logging_config.py`** - Centralized logging setup
- **`rate_limiter.py`** - API rate limiting for Twelve Data
- **`.env`** - Environment variables (API keys)

### Testing
- **`tests/`** - Comprehensive test suite using pytest
  - `test_exchange.py` - Order matching and exchange logic
  - `test_trading_book.py` - Portfolio management
  - `test_market_data.py` - Data handling and simulation
  - `test_user_actions.py` - User interaction validation

### Data Flow
1. **Market Data**: Live prices → Exchange → UI updates
2. **Orders**: User input → Validation → Exchange → Fill → Trading Book
3. **Portfolio**: Fills → Position updates → Balance recalculation → UI display

## Development

### Running Tests
```bash
python3 -m pytest                                                         # Run all tests
python3 -m pytest tests/test_exchange.py                                  # Run specific test file
python3 -m pytest tests/test_exchange.py::TestExchange::test_place_order  # Run specific test
```

### Logging
- Application logs stored in `logs/` directory
- Daily log rotation with timestamps
- Use `-v` flag for verbose console output

This architecture provides clean separation of concerns with realistic trading simulation, making it ideal for learning financial markets and trading concepts.
