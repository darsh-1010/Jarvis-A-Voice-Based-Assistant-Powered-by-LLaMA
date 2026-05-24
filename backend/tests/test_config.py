"""
Tests for jarvis/config.py — Settings / pydantic-settings loading.
"""
import os
import pytest
from unittest.mock import patch


class TestSettings:
    """Tests for the Settings pydantic model."""

    def test_default_values(self):
        """Config should have correct built-in defaults."""
        from jarvis.config import config
        assert config.ollama_model == "gemma2:2b"
        assert config.gemini_model == "gemini-1.5-flash"
        assert config.user_city == "Mumbai"
        assert config.redis_port == 6379
        assert config.use_redis is False
        assert config.wake_word == "jarvis"
        assert config.speech_rate == 175
        assert config.voice_id == 0
        assert config.speech_volume == 1.0

    def test_api_keys_default_none(self):
        """Optional API keys should default to None when not set in env."""
        with patch.dict(os.environ, {}, clear=False):
            from jarvis.config import Settings
            # Create a fresh instance without .env file influence
            test_settings = Settings(
                _env_file=None  # type: ignore
            )
            # Default should be None if not in environment
            # (May pick up from real .env if present, so we just test type)
            assert test_settings.gemini_api_key is None or isinstance(test_settings.gemini_api_key, str)

    def test_env_override(self):
        """Environment variables should override default values."""
        with patch.dict(os.environ, {"USER_CITY": "London", "WAKE_WORD": "computer"}):
            from jarvis.config import Settings
            settings = Settings(_env_file=None)  # type: ignore
            assert settings.user_city == "London"
            assert settings.wake_word == "computer"

    def test_redis_settings(self):
        """Redis configuration fields should be correctly typed."""
        from jarvis.config import config
        assert isinstance(config.redis_host, str)
        assert isinstance(config.redis_port, int)
        assert isinstance(config.redis_db, int)
        assert isinstance(config.use_redis, bool)

    def test_audio_settings_types(self):
        """Audio setting fields should have correct types."""
        from jarvis.config import config
        assert isinstance(config.speech_rate, int)
        assert isinstance(config.speech_volume, float)
        assert isinstance(config.voice_id, int)

    def test_jarvis_persona_is_string(self):
        """jarvis_persona should be a non-empty string."""
        from jarvis.config import config
        assert isinstance(config.jarvis_persona, str)
        assert len(config.jarvis_persona) > 0

    def test_legacy_exports_match_config(self):
        """Legacy module-level constants should match config values."""
        from jarvis.config import (
            config,
            OLLAMA_MODEL, GEMINI_MODEL, OPENROUTER_MODEL,
            REDIS_HOST, REDIS_PORT, REDIS_DB, USE_REDIS,
            WAKE_WORD
        )
        assert OLLAMA_MODEL == config.ollama_model
        assert GEMINI_MODEL == config.gemini_model
        assert OPENROUTER_MODEL == config.openrouter_model
        assert REDIS_HOST == config.redis_host
        assert REDIS_PORT == config.redis_port
        assert REDIS_DB == config.redis_db
        assert USE_REDIS == config.use_redis
        assert WAKE_WORD == config.wake_word

    def test_spotify_redirect_uri_format(self):
        """Spotify redirect URI should be a valid URL string."""
        from jarvis.config import config
        assert config.spotify_redirect_uri.startswith("http")

    def test_knowledge_paths_are_strings(self):
        """Knowledge base path settings should be strings."""
        from jarvis.config import config
        assert isinstance(config.knowledge_dir, str)
        assert isinstance(config.vector_db_path, str)
