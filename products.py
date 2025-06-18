from typing import NamedTuple

# Define Product NamedTuple
Product = NamedTuple('Product', [
    ('symbol', str),
    ('name', str),
    ('category', str),
    ('initial_price', float)
])

# Products configuration
DEFAULT_PRODUCTS = [
    # Forex
    Product(symbol="EUR/USD", name="Euro - US Dollar exchange rate", category="forex", initial_price=1.13),
    Product(symbol="GBP/USD", name="British Pound - US Dollar exchange rate", category="forex", initial_price=1.35),
    Product(symbol="USD/JPY", name="US Dollar - Japanese Yen exchange rate", category="forex", initial_price=145.42),

    # Commodities
    Product(symbol="XAU/USD", name="Gold", category="commodities", initial_price=3444.2),
    # Silver is not in our API plan
    # Product(symbol="XAG/USD", name="Silver", category="commodities"),
    # Crude oil is not in our API plan
    # Product(symbol="CL1", name="Crude Oil", category="commodities"),

    # Stocks
    Product(symbol="AAPL", name="Apple Inc.", category="stocks", initial_price=196.8),
    Product(symbol="GOOGL", name="Alphabet Inc. (Google)", category="stocks", initial_price=176.34),
    Product(symbol="MSFT", name="Microsoft Corporation", category="stocks", initial_price=481.17),
    # Product(symbol="AMZN", name="Amazon.com Inc.", category="stocks"),
    # Product(symbol="TSLA", name="Tesla, Inc.", category="stocks")
]

PRODUCTS = DEFAULT_PRODUCTS.copy()
