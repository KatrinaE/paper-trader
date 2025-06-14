# Products configuration
DEFAULT_PRODUCTS = [
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

PRODUCTS = DEFAULT_PRODUCTS.copy()
