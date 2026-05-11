# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
Productivity commands for Jarvis.

Covers: Spotify playback control, Pomodoro focus timer,
language translation, and the morning briefing composite.
"""
import asyncio
import datetime
import logging

from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action


# ──────────────────────────────────────────────
# Spotify Playback
# ──────────────────────────────────────────────

def _get_spotify_client():
    """
    Build and return an authenticated Spotipy client.

    Uses Authorization Code flow with a cached token so subsequent calls
    never require browser re-authentication.

    Returns:
        spotipy.Spotify client, or None if credentials are missing.
    """
    if not config.spotify_client_id or not config.spotify_client_secret:
        return None

    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    scope = "user-read-playback-state user-modify-playback-state"
    auth = SpotifyOAuth(
        client_id=config.spotify_client_id,
        client_secret=config.spotify_client_secret,
        redirect_uri=config.spotify_redirect_uri,
        scope=scope,
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth)


def _spotify_error() -> str:
    """Return a spoken error when Spotify credentials are absent."""
    return "Spotify credentials are not configured, sir. Please add them to your .env file."


@registry.register(name="spotify_play", description="Search for and play a song or artist on Spotify.")
def spotify_play(song_name: str) -> str:
    """
    Search Spotify for a track and start playback on the active device.

    Args:
        song_name: Track or artist name to search for.

    Returns:
        Spoken confirmation string.
    """
    client = _get_spotify_client()
    if not client:
        return _spotify_error()

    log_action("SPOTIFY_PLAY", f"Query: {song_name}", f"Searching Spotify for '{song_name}'.")
    try:
        results = client.search(q=song_name, type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            return f"I couldn't find '{song_name}' on Spotify, sir."

        track = tracks[0]
        track_uri = track["uri"]
        track_title = track["name"]
        artist = track["artists"][0]["name"]
        client.start_playback(uris=[track_uri])
        log_action("SPOTIFY_PLAY", f"Playing: {track_title} by {artist}", "Playback started.")
        return f"Playing '{track_title}' by {artist} on Spotify, sir."

    except Exception as exc:
        log_action("SPOTIFY_PLAY_ERR", f"Error: {exc}", "Spotify play failed.", level=logging.ERROR)
        return "I had trouble starting Spotify playback, sir."


@registry.register(name="spotify_pause", description="Pause Spotify playback.")
def spotify_pause() -> str:
    """Pause the currently active Spotify playback."""
    client = _get_spotify_client()
    if not client:
        return _spotify_error()

    log_action("SPOTIFY_PAUSE", "Pause command", "Pausing Spotify.")
    try:
        client.pause_playback()
        return "Spotify paused, sir."
    except Exception as exc:
        log_action("SPOTIFY_PAUSE_ERR", f"Error: {exc}", "Spotify pause failed.", level=logging.ERROR)
        return "I couldn't pause Spotify, sir."


@registry.register(name="spotify_next", description="Skip to the next track on Spotify.")
def spotify_next() -> str:
    """Skip to the next track in the Spotify queue."""
    client = _get_spotify_client()
    if not client:
        return _spotify_error()

    log_action("SPOTIFY_NEXT", "Next track command", "Skipping to next track.")
    try:
        client.next_track()
        return "Skipped to the next track, sir."
    except Exception as exc:
        log_action("SPOTIFY_NEXT_ERR", f"Error: {exc}", "Spotify skip failed.", level=logging.ERROR)
        return "I couldn't skip the track, sir."


@registry.register(name="spotify_previous", description="Go back to the previous track on Spotify.")
def spotify_previous() -> str:
    """Return to the previous Spotify track."""
    client = _get_spotify_client()
    if not client:
        return _spotify_error()

    log_action("SPOTIFY_PREV", "Previous track command", "Going to previous track.")
    try:
        client.previous_track()
        return "Going back to the previous track, sir."
    except Exception as exc:
        log_action("SPOTIFY_PREV_ERR", f"Error: {exc}", "Spotify previous failed.", level=logging.ERROR)
        return "I couldn't go back to the previous track, sir."


# ──────────────────────────────────────────────
# Pomodoro Timer
# ──────────────────────────────────────────────

# Default session and break durations in minutes
_POMODORO_FOCUS_MINUTES = 25
_POMODORO_BREAK_MINUTES = 5


@registry.register(
    name="start_pomodoro",
    description="Start a Pomodoro focus timer. Default is 25 minutes of focus.",
)
async def start_pomodoro(minutes: int = _POMODORO_FOCUS_MINUTES) -> str:
    """
    Start a Pomodoro-style focus countdown and notify when it expires.

    The timer runs as an asyncio background task so it does not block
    the main voice listening loop.

    Args:
        minutes: Focus duration in minutes. Defaults to 25.

    Returns:
        Immediate confirmation that the timer has started.
    """
    log_action("POMODORO_START", f"Duration: {minutes}m", f"Starting {minutes}-minute Pomodoro timer.")

    async def _countdown():
        await asyncio.sleep(minutes * 60)
        log_action("POMODORO_DONE", f"Timer complete: {minutes}m", "Pomodoro session complete.")
        # Speak via a fresh TTS engine — the main loop may be idle by this point
        from jarvis.audio import AudioManager
        audio = AudioManager()
        await audio.speak(
            f"Your {minutes}-minute focus session is complete, sir. Time to take a short break."
        )

    asyncio.create_task(_countdown())
    return f"Your {minutes}-minute Pomodoro timer has started, sir. I'll notify you when it ends."


# ──────────────────────────────────────────────
# Language Translation
# ──────────────────────────────────────────────

@registry.register(
    name="translate_text",
    description="Translate a phrase from one language to another. "
                "Example: translate 'Good morning' to French.",
)
def translate_text(text: str, target_language: str = "es") -> str:
    """
    Translate text into the specified target language using deep-translator.

    Args:
        text:            The phrase or sentence to translate.
        target_language: ISO 639-1 language code or full name (e.g. 'fr', 'french', 'ja').

    Returns:
        Spoken-ready translation result string.
    """
    log_action(
        "TRANSLATE",
        f"Text: '{text[:40]}' | Target: {target_language}",
        f"Translating text to {target_language}.",
    )
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target=target_language).translate(text)
        return f"In {target_language}, '{text}' translates to: '{translated}'."
    except Exception as exc:
        log_action("TRANSLATE_ERR", f"Error: {exc}", "Translation failed.", level=logging.ERROR)
        return "I had trouble translating that phrase, sir."


# ──────────────────────────────────────────────
# Morning Briefing
# ──────────────────────────────────────────────

def _build_date_string() -> str:
    """Return a human-friendly date and time string for the briefing."""
    now = datetime.datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M %p")


@registry.register(
    name="morning_briefing",
    description="Give a morning briefing: current date, weather, and top news headline.",
)
def morning_briefing() -> str:
    """
    Compose a spoken morning briefing from date, weather, and news sources.

    Pulls weather from the local weather module and top news from web module.
    Gracefully degrades if any service is unavailable.

    Returns:
        A multi-sentence spoken briefing string.
    """
    log_action("BRIEFING_START", "Composing morning briefing", "Preparing your morning briefing.")

    # Date / time
    date_str = _build_date_string()
    parts = [f"Good morning, sir. Today is {date_str}."]

    # Weather — reuse the registered get_weather function
    try:
        from jarvis.commands.weather import get_weather
        weather_str = get_weather()
        parts.append(weather_str)
    except Exception as exc:
        log_action("BRIEFING_WEATHER_ERR", f"Error: {exc}", "Weather unavailable for briefing.", level=logging.WARNING)

    # Top news headline — reuse the registered fetch_latest_news function
    try:
        from jarvis.commands.web import fetch_latest_news
        headlines = fetch_latest_news("general")
        if headlines:
            parts.append(f"In the news today: {headlines[0]}.")
    except Exception as exc:
        log_action("BRIEFING_NEWS_ERR", f"Error: {exc}", "News unavailable for briefing.", level=logging.WARNING)

    parts.append("Have a productive day, sir.")
    return " ".join(parts)
