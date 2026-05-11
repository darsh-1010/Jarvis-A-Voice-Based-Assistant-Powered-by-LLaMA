# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Finance commands for Jarvis — stocks (Alpha Vantage) and crypto (CoinGecko)."""
import logging

import requests

from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action


# CoinGecko public endpoint — no API key required for the free tier
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Alpha Vantage base URL
_AV_BASE = "https://www.alphavantage.co/query"

# A reasonable timeout that avoids stalling the voice loop on slow markets
_REQUEST_TIMEOUT = 10

# Common coin name → CoinGecko ID mapping so users can say "bitcoin" or "ethereum"
_COIN_ID_MAP: dict[str, str] = {
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "solana": "solana",
    "sol": "solana",
    "cardano": "cardano",
    "ada": "cardano",
    "dogecoin": "dogecoin",
    "doge": "dogecoin",
    "ripple": "ripple",
    "xrp": "ripple",
    "bnb": "binancecoin",
    "binance coin": "binancecoin",
}


# ──────────────────────────────────────────────
# Crypto
# ──────────────────────────────────────────────

@registry.register(
    name="get_crypto_price",
    description="Get the current price of a cryptocurrency (e.g. Bitcoin, Ethereum).",
)
def get_crypto_price(coin: str = "bitcoin") -> str:
    """
    Fetch live crypto price in USD and INR from CoinGecko.

    Args:
        coin: Coin name or ticker (e.g. 'bitcoin', 'btc', 'ethereum').

    Returns:
        A spoken-ready price string.
    """
    coin_key = coin.lower().strip()
    coin_id = _COIN_ID_MAP.get(coin_key, coin_key)
    log_action("FINANCE_CRYPTO", f"Coin: {coin_id}", f"Fetching live price for {coin_id}.")

    try:
        response = requests.get(
            f"{_COINGECKO_BASE}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd,inr"},
            timeout=_REQUEST_TIMEOUT,
        )
        data = response.json()
        prices = data.get(coin_id)
        if not prices:
            return f"I couldn't find price data for {coin}, sir."

        usd = prices.get("usd", 0)
        inr = prices.get("inr", 0)
        return f"{coin.capitalize()} is trading at ${usd:,.2f} USD, or ₹{inr:,.2f} INR."

    except requests.RequestException as exc:
        log_action(
            "FINANCE_CRYPTO_ERR",
            f"Network error: {exc}",
            "I had a network problem fetching crypto prices.",
            level=logging.ERROR,
        )
        return "I couldn't reach the crypto market data service right now, sir."


# ──────────────────────────────────────────────
# Stocks — Alpha Vantage
# ──────────────────────────────────────────────

def _requires_av_key() -> str | None:
    """Return an error message if the Alpha Vantage key is missing, else None."""
    if not config.alpha_vantage_api_key:
        return "The Alpha Vantage API key is not configured, sir. Please add it to your .env file."
    return None


@registry.register(
    name="get_stock_price",
    description="Get the current stock price for a ticker symbol (e.g. AAPL, TCS.BSE).",
)
def get_stock_price(symbol: str) -> str:
    """
    Fetch live stock quote via Alpha Vantage GLOBAL_QUOTE function.

    Args:
        symbol: Stock ticker (e.g. 'AAPL', 'RELIANCE.BSE').

    Returns:
        A spoken-ready price string.
    """
    error = _requires_av_key()
    if error:
        return error

    symbol = symbol.upper().strip()
    log_action("FINANCE_STOCK", f"Symbol: {symbol}", f"Fetching live price for {symbol}.")

    try:
        response = requests.get(
            _AV_BASE,
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": config.alpha_vantage_api_key},
            timeout=_REQUEST_TIMEOUT,
        )
        quote = response.json().get("Global Quote", {})
        price = quote.get("05. price")
        change = quote.get("10. change percent", "N/A")

        if not price:
            return f"I couldn't find a quote for {symbol}, sir. Please check the ticker symbol."

        return f"{symbol} is currently trading at ${float(price):,.2f}, with a change of {change} today."

    except requests.RequestException as exc:
        log_action(
            "FINANCE_STOCK_ERR",
            f"Network error: {exc}",
            f"I couldn't fetch the price for {symbol}.",
            level=logging.ERROR,
        )
        return f"I had a network problem fetching the price for {symbol}, sir."


@registry.register(
    name="get_stock_history",
    description="Get the recent price history for a stock ticker using Yahoo Finance.",
)
def get_stock_history(symbol: str, period: str = "5d") -> str:
    """
    Fetch recent closing price history for a stock via yfinance.

    Args:
        symbol: Stock ticker (e.g. 'AAPL', 'RELIANCE.NS').
        period: Lookback period string (e.g. '5d', '1mo', '3mo').

    Returns:
        A spoken-ready summary of recent price history.
    """
    symbol = symbol.upper().strip()
    log_action("FINANCE_HISTORY", f"Symbol: {symbol} | Period: {period}", f"Fetching price history for {symbol}.")

    try:
        import yfinance as yf  # Imported locally — large dependency, only loaded on demand
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period)

        if history.empty:
            return f"No historical data found for {symbol}, sir."

        first_close = history["Close"].iloc[0]
        last_close = history["Close"].iloc[-1]
        change_pct = ((last_close - first_close) / first_close) * 100
        direction = "up" if change_pct >= 0 else "down"

        return (
            f"{symbol} closed at ${last_close:.2f} in its most recent session. "
            f"Over the last {period} it has moved {direction} {abs(change_pct):.1f}%."
        )

    except Exception as exc:
        log_action(
            "FINANCE_HISTORY_ERR",
            f"yfinance error for {symbol}: {exc}",
            f"I couldn't retrieve the price history for {symbol}.",
            level=logging.ERROR,
        )
        return f"I had trouble fetching the price history for {symbol}, sir."
