
from datetime import date, datetime

import numpy as np
import pandas as pd


# Get real options data from Yahoo Finance
def get_chain(ticker, num_expiries=4):

    import yfinance as yf

    stock = yf.Ticker(ticker)

    # Get the latest closing price
    prices = stock.history(period="1d")
    spot = prices["Close"].iloc[-1]

    today = date.today()
    rows = []

    # Go through the nearest expiration dates
    for expiry in stock.options[:num_expiries]:

        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        days = (expiry_date - today).days
        years = days / 365

        options = stock.option_chain(expiry)

        calls = options.calls
        puts = options.puts

        # Go through calls and puts
        for option_type, table in [("call", calls), ("put", puts)]:

            for _, row in table.iterrows():

                rows.append({
                    "type": option_type,
                    "strike": row["strike"],
                    "expiry": expiry,
                    "years": years,
                    "iv": row["impliedVolatility"],
                    "open_interest": row["openInterest"]
                })

    chain = pd.DataFrame(rows)

    return spot, clean_chain(chain)


# Remove missing or invalid data
def clean_chain(chain):

    chain = chain.dropna(subset=["iv", "open_interest"])

    chain = chain[chain["open_interest"] > 0]
    chain = chain[chain["iv"] > 0]

    chain = chain.reset_index(drop=True)

    return chain


# Make sample data for testing
def make_sample_chain(spot=600, num_expiries=4, seed=1):

    rng = np.random.default_rng(seed)

    # Make strike prices around the stock price
    low = round(spot * 0.85)
    high = round(spot * 1.15)

    strikes = np.arange(low, high, 5)

    rows = []

    for i in range(num_expiries):

        # Each expiry is one week apart
        days = 2 + i * 7
        years = days / 365

        expiry_date = pd.Timestamp(date.today()) + pd.Timedelta(days=days)
        expiry = expiry_date.strftime("%Y-%m-%d")

        for strike in strikes:

            # Distance from current stock price
            distance = (strike - spot) / spot

            # Estimate implied volatility
            iv = 0.15 - 0.3 * distance + 0.8 * distance**2

            # Make random open interest
            call_oi = rng.integers(500, 5000)
            put_oi = rng.integers(500, 6000)

            # More calls above spot, more puts below
            call_oi = call_oi * np.exp(-((distance - 0.03) / 0.04)**2)
            put_oi = put_oi * np.exp(-((distance + 0.04) / 0.05)**2)

            rows.append({
                "type": "call",
                "strike": strike,
                "expiry": expiry,
                "years": years,
                "iv": iv,
                "open_interest": round(call_oi)
            })

            rows.append({
                "type": "put",
                "strike": strike,
                "expiry": expiry,
                "years": years,
                "iv": iv,
                "open_interest": round(put_oi)
            })

    chain = pd.DataFrame(rows)

    return spot, clean_chain(chain)
