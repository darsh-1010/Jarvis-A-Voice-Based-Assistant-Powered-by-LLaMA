"""Configuration settings for Jarvis."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AI Persona & Tone
JARVIS_PERSONA = "You are Jarvis, a highly sophisticated AI assistant. You are helpful, polite, and efficient. Use 'sir' occasionally."
JARVIS_TONE = "professional" # options: professional, friendly, sarcastic

# AI Model Settings
OLLAMA_MODEL = "gemma2:2b"
GEMINI_MODEL = "gemini-flash-latest"
OPENROUTER_MODEL = "openrouter/free" 

# Hardcoded Paths
SOURCE_FILE_PATH = r"D:\Laptop\Phoneix"

# API Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "17981b970a33437ab4f162eb13ac13a1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Memory Settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
USE_REDIS = False # Set to True if Redis is installed and running

# Audio Settings
SPEECH_RATE = 175 # Slightly faster for professional tone
SPEECH_VOLUME = 1.0
VOICE_ID = 0 # 0 for male, 1 for female (if available)

# Wake Word
WAKE_WORD = "jarvis"

# Provider Preference
# Options: "ollama", "gemini", "openrouter"
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini")
