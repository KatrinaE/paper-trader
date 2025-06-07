# Market Data Terminal

A Python terminal application for streaming commodities and forex market data using Twelve Data API.

## Features
- Real-time market data streaming
- Display bid and offer prices
- Clean terminal interface using Rich
- Support for multiple instruments (forex and commodities)

## Setup
1. Get a free API key from Twelve Data:
   - Visit https://twelvedata.com/
   - Sign up for an account
   - Create an API key in your dashboard

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API key:
```
API_KEY=your_twelvedata_api_key_here
```

4. Run the application:
```bash
python main.py
```

## Configuration
The application is configured to monitor:
- EUR/USD (Euro - US Dollar exchange rate)
- XAU/USD (Gold)
- XAG/USD (Silver)

You can modify the instruments in `main.py` under the `INSTRUMENTS` dictionary.
