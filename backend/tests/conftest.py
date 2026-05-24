"""
Shared pytest fixtures for the Jarvis backend test suite.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock


# ──────────────────────────────────────────────
# asyncio mode: make all tests async by default
# ──────────────────────────────────────────────
# Set in pytest.ini: asyncio_mode = auto


@pytest.fixture
def mock_config(mocker):
    """Patch jarvis.config.config with predictable test values."""
    cfg = MagicMock()
    cfg.gemini_api_key = "test-gemini-key"
    cfg.openrouter_api_key = "test-openrouter-key"
    cfg.ollama_model = "test-model"
    cfg.gemini_model = "gemini-1.5-flash"
    cfg.openrouter_model = "test/router-model"
    cfg.jarvis_persona = "You are a test assistant."
    cfg.use_redis = False
    cfg.redis_host = "localhost"
    cfg.redis_port = 6379
    cfg.redis_db = 0
    cfg.news_api_key = "test-news-key"
    cfg.openweathermap_api_key = "test-owm-key"
    cfg.user_city = "TestCity"
    cfg.spotify_client_id = "test-spotify-id"
    cfg.spotify_client_secret = "test-spotify-secret"
    cfg.spotify_redirect_uri = "http://localhost:8888/callback"
    cfg.source_file_path = r"C:\test\path"
    cfg.vector_db_path = "./test_vector_db"
    cfg.knowledge_dir = "./test_knowledge"
    # Patch in all relevant modules
    mocker.patch("jarvis.brain.config", cfg)
    mocker.patch("jarvis.commands.weather.config", cfg)
    mocker.patch("jarvis.commands.web.config", cfg)
    mocker.patch("jarvis.commands.system.config", cfg)
    mocker.patch("jarvis.commands.productivity.config", cfg)
    return cfg


@pytest.fixture
def mock_brain_manager(mocker):
    """Return a lightweight mock BrainManager."""
    manager = MagicMock()
    manager.get_active_provider = AsyncMock()
    manager.generate_response = AsyncMock(return_value="Test response from brain.")
    return manager
