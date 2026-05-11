# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
import json
import os
from jarvis.logger import logger

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "persona": "You are Jarvis, a highly sophisticated AI assistant. You are helpful, polite, and efficient. Use 'sir' occasionally.",
    "tone": "professional", # professional, friendly, sarcastic
    "voice_id": 0,
    "speech_rate": 175,
    "sensitivity": "High",
    "language": "English (US)",
    "dark_mode": False
}

class SettingsManager:
    """Manages dynamic system settings with local persistence."""
    
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Load settings from JSON file."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
                logger.info("[SETTINGS] Successfully loaded dynamic settings.")
            except Exception as e:
                logger.error(f"[SETTINGS] Failed to load settings: {e}")

    def save(self):
        """Save current settings to JSON file."""
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
            logger.info("[SETTINGS] Successfully saved dynamic settings.")
        except Exception as e:
            logger.error(f"[SETTINGS] Failed to save settings: {e}")

    def get(self, key, default=None):
        """Get a specific setting."""
        return self.settings.get(key, default)

    def update(self, key_or_dict, value=None):
        """Update settings."""
        if isinstance(key_or_dict, dict):
            self.settings.update(key_or_dict)
        else:
            self.settings[key_or_dict] = value
        self.save()

# Global instance
settings_manager = SettingsManager()
