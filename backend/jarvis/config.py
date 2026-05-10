# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """System-wide configuration using Pydantic Settings."""
    
    # AI Persona & Tone
    jarvis_persona: str = "You are Jarvis, a highly sophisticated AI assistant. You are helpful, polite, and efficient. Use 'sir' occasionally."
    jarvis_tone: str = "professional"
    
    # AI Model Settings
    ollama_model: str = "gemma2:2b"
    gemini_model: str = "gemini-1.5-flash"
    openrouter_model: str = "google/gemma-2-9b-it:free"
    
    # API Keys
    news_api_key: Optional[str] = "17981b970a33437ab4f162eb13ac13a1"
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
    
    # Provider Preference
    default_provider: str = "gemini"
    
    # Paths
    source_file_path: str = r"C:\Users\10102\Downloads\Jarvis"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Global config instance
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

