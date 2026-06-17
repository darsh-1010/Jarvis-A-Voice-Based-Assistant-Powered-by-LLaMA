# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Dynamic settings manager with live config patching and persona integration."""

import json
import os
from typing import Any

from jarvis.logger import logger
from jarvis.persona import TONE_MODIFIERS, TONE_PRESETS, build_persona

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "persona_custom": "",  # empty = use tone preset; non-empty = full override
    "tone": "professional",
    "voice_id": 0,
    "speech_rate": 175,
    "sensitivity": "High",
    "language": "English (US)",
    "dark_mode": False,
}


class SettingsManager:
    """Manages dynamic system settings with local persistence and live config patching."""

    def __init__(self) -> None:
        """Load persisted settings or fall back to defaults."""
        self.settings: dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self) -> None:
        """Load settings from JSON file, merging with defaults for any missing keys."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
                data = json.load(settings_file)
                self.settings.update(data)
            logger.info("[SETTINGS] Successfully loaded dynamic settings.")
        except (OSError, ValueError) as exc:
            logger.error("[SETTINGS] Failed to load settings: %s", exc)

    def save(self) -> None:
        """Persist current settings to JSON file."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
                json.dump(self.settings, settings_file, indent=4)
            logger.info("[SETTINGS] Successfully saved dynamic settings.")
        except (OSError, ValueError) as exc:
            logger.error("[SETTINGS] Failed to save settings: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for a settings key, or default if absent."""
        return self.settings.get(key, default)

    def update(self, key_or_dict: Any, value: Any = None) -> None:
        """Update one or more settings and persist immediately."""
        if isinstance(key_or_dict, dict):
            self.settings.update(key_or_dict)
        else:
            self.settings[key_or_dict] = value
        self.save()

    def apply_to_config(self, config: Any) -> None:
        """Patch the live config object so the next LLM call uses updated settings.

        Args:
            config: The global Settings instance from jarvis.config.
        """
        tone = self.settings.get("tone", "professional")
        custom_override = self.settings.get("persona_custom", "")
        config.jarvis_persona = build_persona(
            tone=tone, custom_override=custom_override
        )
        config.jarvis_tone = tone

        speech_rate = self.settings.get("speech_rate")
        if isinstance(speech_rate, int):
            config.speech_rate = speech_rate

        voice_id = self.settings.get("voice_id")
        if isinstance(voice_id, int):
            config.voice_id = voice_id

        logger.info("[SETTINGS] Live config patched | Tone: %s | Rate: %s", tone, speech_rate)

    @staticmethod
    def list_tone_presets() -> list[dict[str, str]]:
        """Return tone presets with their labels and descriptions for the UI.

        Returns:
            List of dicts with 'id', 'label', and 'description' keys.
        """
        descriptions = {
            "professional": "Formal, precise, and composed. The classic Jarvis.",
            "friendly": "Warm and conversational. A knowledgeable colleague.",
            "sarcastic": "Dry wit and understated humour. Never boring.",
        }
        return [
            {
                "id": tone,
                "label": tone.capitalize(),
                "description": descriptions.get(tone, ""),
            }
            for tone in TONE_PRESETS
            if tone in TONE_MODIFIERS
        ]


# Global instance — all modules import this
settings_manager = SettingsManager()
