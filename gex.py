
import numpy as np
from scipy.stats import norm

CONTRACT_SIZE = 100
RATE = 0.04


# Calculate gamma for each option
def bs_gamma(spot, strike, years, iv):

    # Avoid dividing by zero
    years = np.maximum(years, 1 / 365)
    iv = np.maximum(iv, 0.01)

    # Black-Scholes formula
    top = np.log(spot / strike) + (RATE + 0.5 * iv**2) * years
    bottom = iv * np.sqrt(years)

    d1 = top / bottom

    gamma = norm.pdf(d1) / (spot * bottom)

    return gamma


# Add gamma and GEX to the option chain
def add_gex(chain, spot):

    chain = chain.copy()

    # Calculate gamma
    chain["gamma"] = bs_gamma(
        spot,
        chain["strike"],
        chain["years"],
        chain["iv"]
    )

    # Calls are positive, puts are negative
    sign = np.where(chain["type"] == "call", 1, -1)

    # Calculate gamma exposure
    chain["gex"] = (
        sign
        * chain["gamma"]
        * chain["open_interest"]
        * CONTRACT_SIZE
        * spot**2
        * 0.01
    )

    return chain


# Calculate total GEX
def total_gex(chain, spot):

    chain = add_gex(chain, spot)

    total = chain["gex"].sum()

    return total


# Calculate GEX for each strike price
def gex_by_strike(chain):

    # Separate calls and puts
    calls = chain[chain["type"] == "call"]
    puts = chain[chain["type"] == "put"]

    # Add GEX at each strike
    call_gex = calls.groupby("strike")["gex"].sum()
    put_gex = puts.groupby("strike")["gex"].sum()

    # Combine into one table
    table = call_gex.to_frame("call_gex")
    table = table.join(put_gex.to_frame("put_gex"), how="outer")

    table = table.fillna(0)

    # Calculate net GEX
    table["net_gex"] = table["call_gex"] + table["put_gex"]

    return table.reset_index()


# Calculate GEX for each expiration date
def gex_by_expiry(chain):

    table = chain.groupby("expiry")["gex"].sum()

    return table.reset_index()


# Find where total GEX crosses zero
def find_gamma_flip(chain, spot, search_range=0.10, steps=200):

    # Test stock prices within 10% of the current price
    low = spot * (1 - search_range)
    high = spot * (1 + search_range)

    prices = np.linspace(low, high, steps)

    # Calculate GEX at each price
    totals = []

    for price in prices:
        gex = total_gex(chain, price)
        totals.append(gex)

    # Look for a change from positive to negative or vice versa
    for i in range(len(prices) - 1):

        first = totals[i]
        second = totals[i + 1]

        if first == 0:
            return prices[i]

        if first * second < 0:

            # Estimate where GEX reaches zero
            difference = second - first
            fraction = -first / difference

            flip = prices[i] + fraction * (prices[i + 1] - prices[i])

            return flip

    if totals[-1] == 0:
        return prices[-1]

    return None


# Find call and put walls
def find_walls(strike_table):

    # Strike with the highest call GEX
    call_index = strike_table["call_gex"].idxmax()
    call_wall = strike_table.loc[call_index, "strike"]

    # Strike with the lowest put GEX
    put_index = strike_table["put_gex"].idxmin()
    put_wall = strike_table.loc[put_index, "strike"]

    return call_wall, put_wall
