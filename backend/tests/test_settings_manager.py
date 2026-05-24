"""
Tests for jarvis/settings_manager.py — SettingsManager persistence.
"""
import json
import os
import pytest
from unittest.mock import mock_open, patch, MagicMock

from jarvis.settings_manager import SettingsManager, DEFAULT_SETTINGS


class TestSettingsManagerDefaults:
    """Tests for default settings initialization."""

    def test_default_settings_are_loaded(self):
        """SettingsManager should initialize with DEFAULT_SETTINGS when no file exists."""
        with patch("jarvis.settings_manager.os.path.exists", return_value=False):
            manager = SettingsManager()
        assert manager.settings == DEFAULT_SETTINGS

    def test_persona_in_defaults(self):
        """DEFAULT_SETTINGS should contain the 'persona' key."""
        assert "persona" in DEFAULT_SETTINGS

    def test_tone_in_defaults(self):
        """DEFAULT_SETTINGS should contain the 'tone' key."""
        assert "tone" in DEFAULT_SETTINGS
        assert DEFAULT_SETTINGS["tone"] == "professional"

    def test_dark_mode_default_is_false(self):
        """Dark mode should default to False."""
        assert DEFAULT_SETTINGS["dark_mode"] is False


class TestSettingsManagerLoad:
    """Tests for the load() method."""

    def test_load_reads_from_json_file(self):
        """load() should update settings from a valid JSON file."""
        data = {"tone": "sarcastic", "dark_mode": True}
        m = mock_open(read_data=json.dumps(data))
        with patch("jarvis.settings_manager.os.path.exists", return_value=True), \
             patch("builtins.open", m):
            manager = SettingsManager()
        assert manager.settings["tone"] == "sarcastic"
        assert manager.settings["dark_mode"] is True

    def test_load_invalid_json_does_not_crash(self):
        """load() should not raise on invalid JSON — falls back to defaults."""
        m = mock_open(read_data="invalid json {{")
        with patch("jarvis.settings_manager.os.path.exists", return_value=True), \
             patch("builtins.open", m):
            manager = SettingsManager()
        # Should still have default values
        assert "persona" in manager.settings

    def test_load_no_file_uses_defaults(self):
        """load() should leave settings as defaults when no file exists."""
        with patch("jarvis.settings_manager.os.path.exists", return_value=False):
            manager = SettingsManager()
        assert manager.settings == DEFAULT_SETTINGS


class TestSettingsManagerGet:
    """Tests for the get() method."""

    @pytest.fixture
    def manager(self):
        with patch("jarvis.settings_manager.os.path.exists", return_value=False):
            return SettingsManager()

    def test_get_existing_key(self, manager):
        """get() should return the correct value for a known key."""
        assert manager.get("tone") == "professional"

    def test_get_missing_key_with_default(self, manager):
        """get() should return the provided default for an unknown key."""
        assert manager.get("nonexistent_key", "fallback") == "fallback"

    def test_get_missing_key_no_default(self, manager):
        """get() should return None for an unknown key with no default."""
        assert manager.get("ghost_key") is None


class TestSettingsManagerUpdate:
    """Tests for the update() method."""

    @pytest.fixture
    def manager(self):
        with patch("jarvis.settings_manager.os.path.exists", return_value=False):
            mgr = SettingsManager()
        mgr.save = MagicMock()  # Prevent file I/O
        return mgr

    def test_update_single_key(self, manager):
        """update() with key+value should update the settings dict."""
        manager.update("tone", "friendly")
        assert manager.settings["tone"] == "friendly"

    def test_update_calls_save(self, manager):
        """update() should call save() to persist changes."""
        manager.update("dark_mode", True)
        manager.save.assert_called_once()

    def test_update_with_dict(self, manager):
        """update() with a dict should merge all keys."""
        manager.update({"tone": "casual", "dark_mode": True})
        assert manager.settings["tone"] == "casual"
        assert manager.settings["dark_mode"] is True


class TestSettingsManagerSave:
    """Tests for the save() method."""

    @pytest.fixture
    def manager(self):
        with patch("jarvis.settings_manager.os.path.exists", return_value=False):
            return SettingsManager()

    def test_save_writes_json(self, manager):
        """save() should write settings as JSON to the settings file."""
        m = mock_open()
        with patch("builtins.open", m):
            manager.save()
        m.assert_called_once()
        # Check json.dump was effectively called (handle was written)
        written = "".join(call.args[0] for call in m().write.call_args_list)
        data = json.loads(written)
        assert "tone" in data

    def test_save_handles_io_error(self, manager, caplog):
        """save() should log an error gracefully on IOError."""
        import logging
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with caplog.at_level(logging.ERROR, logger="jarvis"):
                manager.save()
        assert "Failed to save" in caplog.text
