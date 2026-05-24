"""
Tests for api/main.py — FastAPI endpoints.
Tests call the async route handlers directly to avoid TestClient/httpx version mismatches.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# Import app and immediately replace global dependencies to prevent side-effects
import api.main
from api.main import root, chat, get_stats, control_volume, get_settings, update_settings
from api.models import ChatRequest, SettingsUpdate

# Replace the global brain with a mock
mock_brain = MagicMock()
mock_brain.generate_response = AsyncMock(return_value="Test brain response.")
api.main.brain = mock_brain


# ──────────────────────────────────────────────
# GET /
# ──────────────────────────────────────────────

class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_online_status(self):
        response = await root()
        assert response["status"] == "online"
        assert response["assistant"] == "Jarvis"
        assert response["version"] == "3.0.0"


# ──────────────────────────────────────────────
# POST /chat
# ──────────────────────────────────────────────

class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        mock_brain.generate_response.return_value = "Hello, sir."
        req = ChatRequest(message="Hello Jarvis")
        response = await chat(req)
        assert response.response == "Hello, sir."
        assert response.history == []

    @pytest.mark.asyncio
    async def test_chat_calls_brain_with_lowercase(self):
        mock_brain.generate_response.return_value = "Sure."
        req = ChatRequest(message="OPEN NOTEPAD")
        await chat(req)
        call_args = mock_brain.generate_response.call_args[0][0]
        assert call_args == "open notepad"

    @pytest.mark.asyncio
    async def test_chat_empty_message(self):
        mock_brain.generate_response.return_value = "I didn't hear anything."
        req = ChatRequest(message="")
        response = await chat(req)
        assert response.response == "I didn't hear anything."

    @pytest.mark.asyncio
    async def test_chat_tool_match_invokes_registry(self, mocker):
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.list_tools.return_value = [
            {"name": "get_weather", "description": "Get weather."}
        ]
        mock_registry.invoke = AsyncMock(return_value="Sunny, 25°C.")
        req = ChatRequest(message="get weather now")
        response = await chat(req)
        assert response.response == "Sunny, 25°C."


# ──────────────────────────────────────────────
# GET /system/stats
# ──────────────────────────────────────────────

class TestSystemStatsEndpoint:
    @pytest.mark.asyncio
    async def test_stats_returns_correct_fields(self, mocker):
        mock_psutil = mocker.patch("api.main.psutil")
        mock_psutil.cpu_percent.return_value = 10.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=20.0)
        mock_psutil.disk_usage.return_value = MagicMock(percent=30.0)
        mock_psutil.boot_time.return_value = 0.0
        
        response = await get_stats()
        assert response.cpu_percent == 10.0
        assert response.ram_percent == 20.0
        assert response.disk_usage == 30.0
        assert hasattr(response, "boot_time")


# ──────────────────────────────────────────────
# POST /commands/volume/{direction}
# ──────────────────────────────────────────────

class TestVolumeEndpoint:
    @pytest.mark.asyncio
    async def test_volume_up_invokes_correct_tool(self, mocker):
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.invoke = AsyncMock(return_value=None)
        response = await control_volume("up")
        mock_registry.invoke.assert_called_once_with("volume_up")
        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_volume_down_invokes_correct_tool(self, mocker):
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.invoke = AsyncMock(return_value=None)
        response = await control_volume("down")
        mock_registry.invoke.assert_called_once_with("volume_down")
        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_volume_invalid_direction_raises_400(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await control_volume("sideways")
        assert exc_info.value.status_code == 400


# ──────────────────────────────────────────────
# GET & POST /settings
# ──────────────────────────────────────────────

class TestSettingsEndpoints:
    @pytest.mark.asyncio
    async def test_get_settings_returns_dict(self):
        response = await get_settings()
        assert isinstance(response, dict)

    @pytest.mark.asyncio
    async def test_post_settings_returns_success(self):
        req = SettingsUpdate(tone="friendly")
        response = await update_settings(req)
        assert response["status"] == "success"
