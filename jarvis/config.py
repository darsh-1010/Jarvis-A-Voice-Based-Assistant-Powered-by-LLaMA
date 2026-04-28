"""Configuration settings for Jarvis."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AI Model Settings
OLLAMA_MODEL = "gemma2:2b"

# API Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "17981b970a33437ab4f162eb13ac13a1")

# Hardcoded Paths
# Warning: This path may need to be updated based on your system
SOURCE_FILE_PATH = r"D:\Laptop\Phoneix"

# Audio Settings
SPEECH_RATE = 150
SPEECH_VOLUME = 1.0

# Wake Word
WAKE_WORD = "jarvis"
