# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Weather commands for Jarvis using the OpenWeatherMap API."""
import logging

import requests

from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action


# OpenWeatherMap base URL — v2.5 is stable and covered by the free tier
_OWM_BASE = "https://api.openweathermap.org/data/2.5"

# Free tier allows 1,000 calls/day; a 10-second timeout is generous for a
# REST weather call and prevents the voice loop from stalling on network issues.
_REQUEST_TIMEOUT = 10


def _requires_api_key() -> str | None:
    """Return an error message if the API key is missing, else None."""
    if not config.openweathermap_api_key:
        return "The OpenWeatherMap API key is not configured, sir. Please add it to your .env file."
    return None


def _fetch_weather_data(city: str, endpoint: str, extra_params: dict) -> dict | None:
    """
    Fetch data from the OWM API for a given city and endpoint.

    Args:
        city:        City name to query.
        endpoint:    OWM endpoint path (e.g. 'weather' or 'forecast').
        extra_params: Additional query params to merge.

    Returns:
        Parsed JSON dict on success, None on any error.
    """
    params = {
        "q": city,
        "appid": config.openweathermap_api_key,
        "units": "metric",
        **extra_params,
    }
    try:
        response = requests.get(f"{_OWM_BASE}/{endpoint}", params=params, timeout=_REQUEST_TIMEOUT)
        data = response.json()
        if data.get("cod") not in (200, "200"):
            log_action(
                "WEATHER_API_ERR",
                f"OWM error for '{city}': {data.get('message')}",
                f"I couldn't fetch weather for {city}.",
                level=logging.WARNING,
            )
            return None
        return data
    except requests.RequestException as exc:
        log_action(
            "WEATHER_NET_ERR",
            f"Network error: {exc}",
            "I had a network problem fetching the weather.",
            level=logging.ERROR,
        )
        return None


@registry.register(name="get_weather", description="Get the current weather for a city.")
def get_weather(city: str = "") -> str:
    """
    Fetch current weather conditions for a city.

    Args:
        city: City name to query. Falls back to USER_CITY from config.

    Returns:
        A spoken-ready weather summary string.
    """
    target_city = city.strip() or config.user_city
    log_action("WEATHER_NOW", f"City: {target_city}", f"Fetching current weather for {target_city}.")

    error = _requires_api_key()
    if error:
        return error

    data = _fetch_weather_data(target_city, "weather", {})
    if not data:
        return f"I couldn't retrieve the weather for {target_city} right now, sir."

    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    description = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]
    return (
        f"In {target_city} it is currently {temp:.1f}°C, feels like {feels_like:.1f}°C, "
        f"with {description}. Humidity is at {humidity}%."
    )


@registry.register(
    name="get_forecast",
    description="Get a 3-day weather forecast for a city.",
)
def get_forecast(city: str = "") -> str:
    """
    Fetch a brief 3-day forecast for a city using the OWM /forecast endpoint.

    Args:
        city: City name. Falls back to USER_CITY from config.

    Returns:
        A spoken-ready forecast summary string.
    """
    target_city = city.strip() or config.user_city
    log_action("WEATHER_FORECAST", f"City: {target_city}", f"Fetching 3-day forecast for {target_city}.")

    error = _requires_api_key()
    if error:
        return error

    # cnt=8 gives 8 × 3-hour slots ≈ 24 hours; enough for a meaningful daily summary
    data = _fetch_weather_data(target_city, "forecast", {"cnt": 8})
    if not data:
        return f"I couldn't retrieve the forecast for {target_city}, sir."

    items = data.get("list", [])
    if not items:
        return f"No forecast data available for {target_city}, sir."

    temps = [item["main"]["temp"] for item in items]
    descriptions = [item["weather"][0]["description"] for item in items]
    min_temp = min(temps)
    max_temp = max(temps)
    # Most common description across the forecast window
    dominant = max(set(descriptions), key=descriptions.count)
    return (
        f"For {target_city} over the next 24 hours: expect {dominant}, "
        f"with temperatures ranging from {min_temp:.1f}°C to {max_temp:.1f}°C."
    )
