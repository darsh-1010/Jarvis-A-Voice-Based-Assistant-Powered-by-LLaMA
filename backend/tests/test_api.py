"""
Tests for api/main.py — FastAPI endpoints.
Tests call the async route handlers directly, using MagicMock for the FastAPI
Request object so that app.state.brain / app.state.intent_router can be injected
without a real server.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from api.models import ChatRequest, SettingsUpdate


# ──────────────────────────────────────────────
# Shared Mock Helpers
# ──────────────────────────────────────────────

def _make_mock_request(brain=None, intent_router=None):
    """Build a minimal FastAPI Request mock with the expected app.state fields."""
    mock_brain = brain or MagicMock()
    mock_brain.generate_response = AsyncMock(return_value="Test brain response.")
    mock_brain.redis = None  # No Redis in tests

    mock_intent_router = intent_router or MagicMock()
    mock_intent_router.classify = AsyncMock(
        return_value=MagicMock(tool_name=None, params={})
    )

    mock_app = MagicMock()
    mock_app.state.brain = mock_brain
    mock_app.state.intent_router = mock_intent_router

    mock_request = MagicMock()
    mock_request.app = mock_app
    return mock_request, mock_brain, mock_intent_router


# ──────────────────────────────────────────────
# GET /
# ──────────────────────────────────────────────

class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_online_status(self):
        from api.main import root
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
        from api.main import chat
        mock_request, mock_brain, mock_intent_router = _make_mock_request()
        mock_brain.generate_response.return_value = "Hello, sir."
        # intent_router returns no tool match → falls back to brain
        mock_intent_router.classify.return_value = MagicMock(tool_name=None, params={})

        body = ChatRequest(message="Hello Jarvis")
        response = await chat(mock_request, body)
        assert response.response == "Hello, sir."
        assert response.history == []

    @pytest.mark.asyncio
    async def test_chat_calls_brain_with_stripped_message(self):
        from api.main import chat
        mock_request, mock_brain, mock_intent_router = _make_mock_request()
        mock_brain.generate_response.return_value = "Sure."
        mock_intent_router.classify.return_value = MagicMock(tool_name=None, params={})

        body = ChatRequest(message="  OPEN NOTEPAD  ")
        await chat(mock_request, body)
        # Verify classify was called with stripped message
        call_text = mock_intent_router.classify.call_args[0][0]
        assert call_text == "OPEN NOTEPAD"

    @pytest.mark.asyncio
    async def test_chat_empty_message(self):
        from api.main import chat
        mock_request, mock_brain, mock_intent_router = _make_mock_request()
        mock_brain.generate_response.return_value = "I didn't hear anything."
        mock_intent_router.classify.return_value = MagicMock(tool_name=None, params={})

        body = ChatRequest(message="")
        response = await chat(mock_request, body)
        assert response.response == "I didn't hear anything."

    @pytest.mark.asyncio
    async def test_chat_tool_match_invokes_registry(self, mocker):
        from api.main import chat
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.list_tools.return_value = [
            {"name": "get_weather", "description": "Get weather."}
        ]
        mock_registry.invoke = AsyncMock(return_value="Sunny, 25°C.")

        mock_request, mock_brain, mock_intent_router = _make_mock_request()
        mock_intent_router.classify.return_value = MagicMock(
            tool_name="get_weather", params={"city": "Mumbai"}
        )

        body = ChatRequest(message="what's the weather in Mumbai")
        response = await chat(mock_request, body)
        assert response.response == "Sunny, 25°C."
        mock_registry.invoke.assert_called_once_with("get_weather", city="Mumbai")


# ──────────────────────────────────────────────
# GET /system/stats
# ──────────────────────────────────────────────

class TestSystemStatsEndpoint:
    @pytest.mark.asyncio
    async def test_stats_returns_correct_fields(self, mocker):
        from api.main import get_stats
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
        from api.main import control_volume
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.invoke = AsyncMock(return_value=None)
        response = await control_volume("up")
        mock_registry.invoke.assert_called_once_with("volume_up")
        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_volume_down_invokes_correct_tool(self, mocker):
        from api.main import control_volume
        mock_registry = mocker.patch("api.main.registry")
        mock_registry.invoke = AsyncMock(return_value=None)
        response = await control_volume("down")
        mock_registry.invoke.assert_called_once_with("volume_down")
        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_volume_invalid_direction_raises_400(self):
        from api.main import control_volume
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
        from api.main import get_settings
        response = await get_settings()
        assert isinstance(response, dict)

    @pytest.mark.asyncio
    async def test_post_settings_returns_success(self):
        from api.main import update_settings
        req = SettingsUpdate(tone="friendly")
        response = await update_settings(req)
        assert response["status"] == "success"
