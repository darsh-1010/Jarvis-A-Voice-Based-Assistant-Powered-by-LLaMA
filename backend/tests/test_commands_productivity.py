"""
Tests for jarvis/commands/productivity.py — Spotify, Pomodoro, translate, briefing.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSpotifyMissingCredentials:
    """Tests for Spotify commands when credentials are absent."""

    def test_spotify_play_no_credentials(self, mocker):
        """spotify_play should return an error message without credentials."""
        mocker.patch("jarvis.commands.productivity.config.spotify_client_id", None)
        mocker.patch("jarvis.commands.productivity.config.spotify_client_secret", None)
        from jarvis.commands.productivity import spotify_play
        result = spotify_play("Bohemian Rhapsody")
        assert "not configured" in result.lower() or "credentials" in result.lower()

    def test_spotify_pause_no_credentials(self, mocker):
        """spotify_pause should return an error message without credentials."""
        mocker.patch("jarvis.commands.productivity.config.spotify_client_id", None)
        mocker.patch("jarvis.commands.productivity.config.spotify_client_secret", None)
        from jarvis.commands.productivity import spotify_pause
        result = spotify_pause()
        assert "not configured" in result.lower() or "credentials" in result.lower()

    def test_spotify_next_no_credentials(self, mocker):
        """spotify_next should return an error message without credentials."""
        mocker.patch("jarvis.commands.productivity.config.spotify_client_id", None)
        mocker.patch("jarvis.commands.productivity.config.spotify_client_secret", None)
        from jarvis.commands.productivity import spotify_next
        result = spotify_next()
        assert "not configured" in result.lower() or "credentials" in result.lower()

    def test_spotify_previous_no_credentials(self, mocker):
        """spotify_previous should return an error message without credentials."""
        mocker.patch("jarvis.commands.productivity.config.spotify_client_id", None)
        mocker.patch("jarvis.commands.productivity.config.spotify_client_secret", None)
        from jarvis.commands.productivity import spotify_previous
        result = spotify_previous()
        assert "not configured" in result.lower() or "credentials" in result.lower()


class TestSpotifyWithMockedClient:
    """Tests for Spotify commands with a mocked Spotipy client."""

    @pytest.fixture
    def mock_spotify_client(self, mocker):
        """Provide a mock Spotipy client and set fake credentials."""
        mocker.patch("jarvis.commands.productivity.config.spotify_client_id", "fake-id")
        mocker.patch("jarvis.commands.productivity.config.spotify_client_secret", "fake-secret")
        mocker.patch("jarvis.commands.productivity.config.spotify_redirect_uri",
                     "http://localhost:8888/callback")
        mock_client = MagicMock()
        mocker.patch("jarvis.commands.productivity._get_spotify_client",
                     return_value=mock_client)
        return mock_client

    def test_spotify_play_found(self, mock_spotify_client):
        """spotify_play should start playback and return a confirmation."""
        mock_spotify_client.search.return_value = {
            "tracks": {
                "items": [{
                    "uri": "spotify:track:123",
                    "name": "Bohemian Rhapsody",
                    "artists": [{"name": "Queen"}]
                }]
            }
        }
        from jarvis.commands.productivity import spotify_play
        result = spotify_play("Bohemian Rhapsody")
        assert "Bohemian Rhapsody" in result
        assert "Queen" in result
        mock_spotify_client.start_playback.assert_called_once()

    def test_spotify_play_not_found(self, mock_spotify_client):
        """spotify_play should return 'not found' when no tracks returned."""
        mock_spotify_client.search.return_value = {"tracks": {"items": []}}
        from jarvis.commands.productivity import spotify_play
        result = spotify_play("nonexistent song xyz")
        assert "couldn't find" in result.lower() or "not found" in result.lower()

    def test_spotify_play_exception(self, mock_spotify_client):
        """spotify_play should handle API exceptions gracefully."""
        mock_spotify_client.search.side_effect = Exception("Spotify API error")
        from jarvis.commands.productivity import spotify_play
        result = spotify_play("test song")
        assert "trouble" in result.lower()

    def test_spotify_pause_success(self, mock_spotify_client):
        """spotify_pause should call pause_playback and confirm."""
        from jarvis.commands.productivity import spotify_pause
        result = spotify_pause()
        mock_spotify_client.pause_playback.assert_called_once()
        assert "paused" in result.lower()

    def test_spotify_next_success(self, mock_spotify_client):
        """spotify_next should call next_track and confirm."""
        from jarvis.commands.productivity import spotify_next
        result = spotify_next()
        mock_spotify_client.next_track.assert_called_once()
        assert "next" in result.lower() or "skipped" in result.lower()

    def test_spotify_previous_success(self, mock_spotify_client):
        """spotify_previous should call previous_track and confirm."""
        from jarvis.commands.productivity import spotify_previous
        result = spotify_previous()
        mock_spotify_client.previous_track.assert_called_once()
        assert "previous" in result.lower() or "back" in result.lower()


class TestPomodoro:
    """Tests for the start_pomodoro async command."""

    @pytest.fixture
    def mock_create_task(self, mocker):
        """Mock create_task to close the unawaited coroutine."""
        def side_effect(coro, *args, **kwargs):
            coro.close()
            return MagicMock()
        return mocker.patch("jarvis.commands.productivity.asyncio.create_task", side_effect=side_effect)

    @pytest.mark.asyncio
    async def test_returns_confirmation_immediately(self, mock_create_task):
        """start_pomodoro should return a confirmation string immediately."""
        from jarvis.commands.productivity import start_pomodoro
        result = await start_pomodoro(25)
        assert "25" in result
        assert "Pomodoro" in result or "timer" in result.lower()

    @pytest.mark.asyncio
    async def test_creates_background_task(self, mock_create_task):
        """start_pomodoro should create an asyncio background task."""
        from jarvis.commands.productivity import start_pomodoro
        await start_pomodoro(10)
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_minutes(self, mock_create_task):
        """start_pomodoro should reflect the custom duration in its response."""
        from jarvis.commands.productivity import start_pomodoro
        result = await start_pomodoro(45)
        assert "45" in result


class TestTranslateText:
    """Tests for the translate_text command."""

    def test_successful_translation(self, mocker):
        """translate_text should return the translated phrase."""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Bonjour le monde"
        # GoogleTranslator is imported locally inside the function, so patch at source
        mocker.patch("deep_translator.GoogleTranslator", return_value=mock_translator)
        from jarvis.commands.productivity import translate_text
        result = translate_text("Hello world", target_language="fr")
        assert "Bonjour le monde" in result
        assert "Hello world" in result

    def test_translation_error_returns_fallback(self, mocker):
        """translate_text should return a fallback message on exception."""
        mocker.patch("deep_translator.GoogleTranslator",
                     side_effect=Exception("Translation API down"))
        from jarvis.commands.productivity import translate_text
        result = translate_text("Hello", target_language="fr")
        assert "trouble" in result.lower()

    def test_default_target_language(self, mocker):
        """translate_text should default to Spanish ('es') as target language."""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Hola"
        mock_cls = mocker.patch("deep_translator.GoogleTranslator", return_value=mock_translator)
        from jarvis.commands.productivity import translate_text
        translate_text("Hello")
        # Check that GoogleTranslator was instantiated with target="es"
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs.get("target") == "es"


class TestMorningBriefing:
    """Tests for the morning_briefing composite command."""

    def test_includes_greeting(self, mocker):
        """Morning briefing should start with a 'Good morning' greeting."""
        # Patch at the source modules since briefing imports them locally
        mocker.patch("jarvis.commands.weather.get_weather",
                     return_value="It is 25°C and sunny.")
        mocker.patch("jarvis.commands.web.fetch_latest_news",
                     return_value=["Top news headline today."])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "Good morning" in result

    def test_includes_date(self, mocker):
        """Morning briefing should include the current date."""
        mocker.patch("jarvis.commands.weather.get_weather", return_value="Sunny.")
        mocker.patch("jarvis.commands.web.fetch_latest_news", return_value=[])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        import datetime
        assert str(datetime.datetime.now().year) in result

    def test_includes_weather(self, mocker):
        """Morning briefing should include the weather summary."""
        mocker.patch("jarvis.commands.weather.get_weather",
                     return_value="It is 30°C and partly cloudy.")
        mocker.patch("jarvis.commands.web.fetch_latest_news", return_value=[])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "30°C" in result

    def test_includes_news_headline(self, mocker):
        """Morning briefing should include the top news headline."""
        mocker.patch("jarvis.commands.weather.get_weather", return_value="Clear.")
        mocker.patch("jarvis.commands.web.fetch_latest_news",
                     return_value=["Stocks hit record high."])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "Stocks hit record high." in result

    def test_handles_weather_failure(self, mocker):
        """Morning briefing should not crash when weather call fails."""
        mocker.patch("jarvis.commands.weather.get_weather",
                     side_effect=Exception("Weather API down"))
        mocker.patch("jarvis.commands.web.fetch_latest_news", return_value=[])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "Good morning" in result  # Should still give a partial briefing

    def test_handles_news_failure(self, mocker):
        """Morning briefing should not crash when news call fails."""
        mocker.patch("jarvis.commands.weather.get_weather", return_value="Sunny.")
        mocker.patch("jarvis.commands.web.fetch_latest_news",
                     side_effect=Exception("News API down"))
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "Good morning" in result

    def test_ends_with_closing(self, mocker):
        """Morning briefing should end with a closing message."""
        mocker.patch("jarvis.commands.weather.get_weather", return_value="Nice.")
        mocker.patch("jarvis.commands.web.fetch_latest_news", return_value=[])
        from jarvis.commands.productivity import morning_briefing
        result = morning_briefing()
        assert "productive" in result.lower() or "Have a" in result
