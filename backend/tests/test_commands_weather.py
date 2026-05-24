"""
Tests for jarvis/commands/weather.py — weather commands.
"""
import pytest
from unittest.mock import MagicMock, patch


# Shared fake weather API response
_WEATHER_DATA = {
    "cod": 200,
    "main": {"temp": 28.5, "feels_like": 31.0, "humidity": 75},
    "weather": [{"description": "scattered clouds"}],
}

_FORECAST_DATA = {
    "cod": "200",
    "list": [
        {"main": {"temp": 30.0}, "weather": [{"description": "clear sky"}]},
        {"main": {"temp": 27.0}, "weather": [{"description": "clear sky"}]},
        {"main": {"temp": 25.0}, "weather": [{"description": "partly cloudy"}]},
    ]
}


class TestGetWeather:
    """Tests for get_weather command."""

    def test_returns_string(self, mocker):
        """get_weather should return a string."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "test-key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _WEATHER_DATA
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_weather
        result = get_weather("Mumbai")
        assert isinstance(result, str)

    def test_includes_temperature(self, mocker):
        """Weather report should include the temperature."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _WEATHER_DATA
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_weather
        result = get_weather("Mumbai")
        assert "28.5" in result

    def test_includes_description(self, mocker):
        """Weather report should include the description."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _WEATHER_DATA
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_weather
        result = get_weather("Mumbai")
        assert "scattered clouds" in result

    def test_defaults_to_configured_city(self, mocker):
        """get_weather with empty city should use config.user_city."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Delhi")
        mock_get = mocker.patch("jarvis.commands.weather.requests.get")
        mock_get.return_value.json.return_value = _WEATHER_DATA
        from jarvis.commands.weather import get_weather
        get_weather("")
        params = mock_get.call_args[1]["params"]
        assert params["q"] == "Delhi"

    def test_returns_error_when_no_api_key(self, mocker):
        """get_weather should return an error message when API key is missing."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", None)
        from jarvis.commands.weather import get_weather
        result = get_weather("Paris")
        assert "not configured" in result.lower() or "API key" in result

    def test_returns_error_on_api_failure(self, mocker):
        """get_weather should return fallback when OWM returns error code."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"cod": 404, "message": "city not found"}
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_weather
        result = get_weather("InvalidCity123")
        assert "couldn't retrieve" in result.lower() or "right now" in result

    def test_returns_error_on_network_exception(self, mocker):
        """get_weather should return fallback on network error."""
        import requests
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mocker.patch("jarvis.commands.weather.requests.get",
                     side_effect=requests.RequestException("timeout"))
        from jarvis.commands.weather import get_weather
        result = get_weather("Mumbai")
        assert "couldn't retrieve" in result.lower() or "network" in result.lower()


class TestGetForecast:
    """Tests for get_forecast command."""

    def test_returns_string(self, mocker):
        """get_forecast should return a string."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _FORECAST_DATA
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_forecast
        result = get_forecast("Mumbai")
        assert isinstance(result, str)

    def test_includes_min_max_temp(self, mocker):
        """Forecast should include min and max temperatures."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _FORECAST_DATA
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_forecast
        result = get_forecast("Mumbai")
        assert "25.0" in result  # min
        assert "30.0" in result  # max

    def test_returns_error_when_no_api_key(self, mocker):
        """get_forecast should return error when API key is missing."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", None)
        from jarvis.commands.weather import get_forecast
        result = get_forecast("London")
        assert "not configured" in result.lower() or "API key" in result

    def test_returns_error_on_api_failure(self, mocker):
        """get_forecast should return fallback when API returns error."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"cod": "404", "message": "not found"}
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_forecast
        result = get_forecast("BadCity")
        assert "couldn't retrieve" in result.lower()

    def test_handles_empty_forecast_list(self, mocker):
        """get_forecast should handle empty list from API gracefully."""
        mocker.patch("jarvis.commands.weather.config.openweathermap_api_key", "key")
        mocker.patch("jarvis.commands.weather.config.user_city", "Mumbai")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"cod": "200", "list": []}
        mocker.patch("jarvis.commands.weather.requests.get", return_value=mock_resp)
        from jarvis.commands.weather import get_forecast
        result = get_forecast("Mumbai")
        assert "No forecast" in result or "available" in result
