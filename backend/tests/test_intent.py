"""
Tests for jarvis/intent.py — IntentRouter and prompt building logic.

Strategy:
  - The LLM call is mocked via the BrainManager's get_active_provider().
  - _parse_response is tested directly with various edge-case JSON strings.
  - _build_classification_prompt is tested as a pure function.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from jarvis.intent import IntentRouter, IntentResult, _build_classification_prompt


# ──────────────────────────────────────────────
# Prompt Builder (pure function)
# ──────────────────────────────────────────────

class TestBuildClassificationPrompt:
    """Tests for _build_classification_prompt helper."""

    TOOLS = [
        {"name": "search_google", "description": "Search Google for any topic."},
        {"name": "get_weather", "description": "Get the current weather for a city."},
    ]

    def test_contains_tool_names(self):
        """Prompt should list all tool names."""
        prompt = _build_classification_prompt("find me the weather", self.TOOLS)
        assert "search_google" in prompt
        assert "get_weather" in prompt

    def test_contains_tool_descriptions(self):
        """Prompt should include tool descriptions."""
        prompt = _build_classification_prompt("find me the weather", self.TOOLS)
        assert "Search Google for any topic." in prompt
        assert "Get the current weather for a city." in prompt

    def test_contains_user_command(self):
        """User command should appear in the prompt."""
        cmd = "play something on spotify"
        prompt = _build_classification_prompt(cmd, self.TOOLS)
        assert cmd in prompt

    def test_contains_parameter_hints(self):
        """Prompt should include parameter hints section."""
        prompt = _build_classification_prompt("test", self.TOOLS)
        assert "Parameter hints" in prompt
        assert "fetch_latest_news" in prompt

    def test_empty_tools_returns_prompt(self):
        """Prompt should still be built even with an empty tools list."""
        prompt = _build_classification_prompt("test command", [])
        assert "test command" in prompt


# ──────────────────────────────────────────────
# IntentRouter._parse_response (unit tests)
# ──────────────────────────────────────────────

class TestParseResponse:
    """Tests for the JSON parsing logic in IntentRouter._parse_response."""

    @pytest.fixture
    def router(self, mock_brain_manager):
        return IntentRouter(mock_brain_manager)

    KNOWN = {"search_google", "get_weather", "fetch_latest_news"}

    def test_valid_json_known_tool(self, router):
        """Should return the matched tool name and params."""
        raw = json.dumps({"tool": "get_weather", "params": {"city": "London"}})
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name == "get_weather"
        assert result.params == {"city": "London"}

    def test_valid_json_null_tool(self, router):
        """Should return tool_name=None when model returns null."""
        raw = json.dumps({"tool": None, "params": {}})
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name is None

    def test_valid_json_unknown_tool(self, router):
        """Should return tool_name=None when tool is not in the registry."""
        raw = json.dumps({"tool": "nonexistent_tool", "params": {}})
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name is None

    def test_json_with_markdown_fence(self, router):
        """Should strip ```json ``` fences before parsing."""
        raw = '```json\n{"tool": "search_google", "params": {"query": "AI news"}}\n```'
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name == "search_google"
        assert result.params == {"query": "AI news"}

    def test_invalid_json_falls_back(self, router):
        """Should return tool_name=None on JSON parse failure."""
        result = router._parse_response("this is not json at all", self.KNOWN)
        assert result.tool_name is None

    def test_params_not_dict_defaults_to_empty(self, router):
        """Should default params to empty dict if model returns non-dict."""
        raw = json.dumps({"tool": "get_weather", "params": "London"})
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name == "get_weather"
        assert result.params == {}

    def test_string_null_tool(self, router):
        """Should treat literal string 'null' as no match."""
        raw = json.dumps({"tool": "null", "params": {}})
        result = router._parse_response(raw, self.KNOWN)
        assert result.tool_name is None


# ──────────────────────────────────────────────
# IntentRouter.classify (integration-level)
# ──────────────────────────────────────────────

class TestIntentRouterClassify:
    """Tests for the full classify() flow."""

    TOOLS = [
        {"name": "get_weather", "description": "Get weather for a city."},
        {"name": "search_google", "description": "Search Google."},
    ]

    @pytest.fixture
    def router(self, mock_brain_manager):
        return IntentRouter(mock_brain_manager)

    @pytest.mark.asyncio
    async def test_classify_empty_command_returns_none(self, router):
        """An empty command should immediately return IntentResult(None)."""
        result = await router.classify("", self.TOOLS)
        assert result.tool_name is None

    @pytest.mark.asyncio
    async def test_classify_empty_tools_returns_none(self, router):
        """No registered tools should immediately return IntentResult(None)."""
        result = await router.classify("get the weather", [])
        assert result.tool_name is None

    @pytest.mark.asyncio
    async def test_classify_successful_routing(self, router, mock_brain_manager):
        """classify() should return the tool from the LLM JSON response."""
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = json.dumps(
            {"tool": "get_weather", "params": {"city": "Paris"}}
        )
        mock_brain_manager.get_active_provider.return_value = mock_provider

        result = await router.classify("what's the weather in Paris?", self.TOOLS)
        assert result.tool_name == "get_weather"
        assert result.params == {"city": "Paris"}

    @pytest.mark.asyncio
    async def test_classify_no_provider_returns_none(self, router, mock_brain_manager):
        """classify() should return None tool when no LLM provider is available."""
        mock_brain_manager.get_active_provider.return_value = None
        result = await router.classify("search for cats", self.TOOLS)
        assert result.tool_name is None

    @pytest.mark.asyncio
    async def test_classify_llm_exception_returns_none(self, router, mock_brain_manager):
        """classify() should return None tool when the LLM call raises an exception."""
        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("API timeout")
        mock_brain_manager.get_active_provider.return_value = mock_provider

        result = await router.classify("play some music", self.TOOLS)
        assert result.tool_name is None

    @pytest.mark.asyncio
    async def test_classify_llm_returns_empty_string(self, router, mock_brain_manager):
        """classify() should return None tool when LLM returns empty string."""
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = ""
        mock_brain_manager.get_active_provider.return_value = mock_provider

        result = await router.classify("do something", self.TOOLS)
        assert result.tool_name is None


# ──────────────────────────────────────────────
# IntentResult dataclass
# ──────────────────────────────────────────────

class TestIntentResult:
    """Basic tests for the IntentResult dataclass."""

    def test_default_params_is_empty_dict(self):
        result = IntentResult(tool_name="get_weather")
        assert result.params == {}

    def test_with_params(self):
        result = IntentResult(tool_name="search_google", params={"query": "AI"})
        assert result.params == {"query": "AI"}

    def test_none_tool_name(self):
        result = IntentResult(tool_name=None)
        assert result.tool_name is None
