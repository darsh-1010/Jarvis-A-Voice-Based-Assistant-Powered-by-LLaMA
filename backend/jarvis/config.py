# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""System-wide configuration loaded from the .env file at the project root."""
import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# ──────────────────────────────────────────────
# .env Resolution
# ──────────────────────────────────────────────

# Walk up from this file (backend/jarvis/config.py) to the project root
# so the .env is always found regardless of the working directory.
# Layout: <root>/.env
#             backend/jarvis/config.py  →  ../../  →  <root>
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))         # backend/jarvis/
_BACKEND_DIR = os.path.dirname(_THIS_DIR)                      # backend/
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)                  # <root>
_ENV_FILE = os.path.join(_PROJECT_ROOT, ".env")                # <root>/.env


class Settings(BaseSettings):
    """System-wide configuration using Pydantic Settings."""

    # AI Persona & Tone
    jarvis_persona: str = (
        "You are Jarvis, a highly sophisticated AI assistant. "
        "You are helpful, polite, and efficient. Use 'sir' occasionally."
    )
    jarvis_tone: str = "professional"

    # AI Model Settings
    ollama_model: str = "gemma2:2b"
    gemini_model: str = "gemini-1.5-flash"
    openrouter_model: str = "google/gemma-2-9b-it:free"

    # API Keys — all loaded from .env, never hardcoded
    news_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Memory Settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    use_redis: bool = False

    # Knowledge Base (RAG)
    knowledge_dir: str = "./data/knowledge"
    vector_db_path: str = "./data/vector_db"

    # Audio Settings
    speech_rate: int = 175
    speech_volume: float = 1.0
    voice_id: int = 0

    # Wake Word
    wake_word: str = "jarvis"

    # Provider Preference (overridden by DEFAULT_PROVIDER in .env)
    default_provider: str = "gemini"

    # Paths
    source_file_path: str = r"C:\Users\10102\Downloads\Jarvis"

    model_config = SettingsConfigDict(
        # Absolute path so the .env is found regardless of CWD
        env_file=_ENV_FILE,
        extra="ignore"
    )


# Global config instance — all modules import this
config = Settings()

# ──────────────────────────────────────────────
# Legacy Compatibility Exports
# ──────────────────────────────────────────────
JARVIS_PERSONA = config.jarvis_persona
OLLAMA_MODEL = config.ollama_model
GEMINI_MODEL = config.gemini_model
OPENROUTER_MODEL = config.openrouter_model
GEMINI_API_KEY = config.gemini_api_key
OPENROUTER_API_KEY = config.openrouter_api_key
NEWS_API_KEY = config.news_api_key
REDIS_HOST = config.redis_host
REDIS_PORT = config.redis_port
REDIS_DB = config.redis_db
USE_REDIS = config.use_redis
SPEECH_VOLUME = config.speech_volume
WAKE_WORD = config.wake_word
SOURCE_FILE_PATH = config.source_file_path
