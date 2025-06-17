# Products configuration
DEFAULT_PRODUCTS = [
    # Forex
    {"symbol": "EUR/USD", "name": "Euro - US Dollar exchange rate", "category": "forex", "initial_price": 1.13},
    {"symbol": "GBP/USD", "name": "British Pound - US Dollar exchange rate", "category": "forex", "initial_price": 1.35},
    {"symbol": "USD/JPY", "name": "US Dollar - Japanese Yen exchange rate", "category": "forex", "initial_price": 145.42},

    # Commodities
    {"symbol": "XAU/USD", "name": "Gold", "category": "commodities", "initial_price": 3444.2},
    # Silver is not in our API plan
    # {"symbol": "XAG/USD", "name": "Silver", "category": "commodities"},
    # Crude oil is not in our API plan
    # {"symbol": "CL1", "name": "Crude Oil", "category": "commodities"},

    # Stocks
    {"symbol": "AAPL", "name": "Apple Inc.", "category": "stocks", "initial_price": 196.8},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Google)", "category": "stocks", "initial_price": 176.34},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "category": "stocks", "initial_price": 481.17},
    # {"symbol": "AMZN", "name": "Amazon.com Inc.", "category": "stocks"},
    #{"symbol": "TSLA", "name": "Tesla, Inc.", "category": "stocks"}
]

PRODUCTS = DEFAULT_PRODUCTS.copy()
