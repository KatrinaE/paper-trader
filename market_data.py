import random

from twelvedata.endpoints import TimeSeriesEndpoint, APIUsageEndpoint

from instruments import INSTRUMENTS
from rate_limiter import RateLimiter

# Rate limiting constants
MAX_CALLS_PER_MINUTE = 8
CALL_WINDOW_SECONDS = 60  # 1 minute

# Initialize rate limiter
rate_limiter = RateLimiter(MAX_CALLS_PER_MINUTE, CALL_WINDOW_SECONDS)

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