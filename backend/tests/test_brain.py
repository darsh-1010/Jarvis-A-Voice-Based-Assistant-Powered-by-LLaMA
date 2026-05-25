"""
Tests for jarvis/brain.py — BrainManager and all AI providers.

Strategy:
  - All external SDK calls (Google Gemini, OpenAI, Ollama) are mocked.
  - Redis is mocked so we never touch a real Redis instance.
  - token counting uses tiktoken which runs locally — no mock needed.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ──────────────────────────────────────────────
# GeminiProvider
# ──────────────────────────────────────────────

class TestGeminiProvider:
    """Unit tests for the GeminiProvider class."""

    def test_init_raises_without_api_key(self, mocker):
        """GeminiProvider must raise ValueError when the API key is absent."""
        mocker.patch("jarvis.brain.config.gemini_api_key", None)
        from jarvis.brain import GeminiProvider
        with pytest.raises(ValueError, match="GEMINI_API_KEY missing"):
            GeminiProvider()

    def test_init_success(self, mocker):
        """GeminiProvider should create a google-genai Client at init time."""
        mocker.patch("jarvis.brain.config.gemini_api_key", "test-key")
        mocker.patch("jarvis.brain.config.gemini_model", "gemini-2.0-flash")
        mocker.patch("jarvis.brain.config.jarvis_persona", "You are Jarvis.")
        # Patch the new SDK Client class
        mock_client_cls = mocker.patch("jarvis.brain.google_genai.Client")
        mock_genai_types = mocker.patch("jarvis.brain.genai_types")
        from jarvis.brain import GeminiProvider
        provider = GeminiProvider()
        # Client must be constructed with the API key
        mock_client_cls.assert_called_once_with(api_key="test-key")
        assert provider is not None

    @pytest.mark.asyncio
    async def test_generate_returns_text(self, mocker):
        """generate() should return the .text attribute from the Gemini response."""
        mocker.patch("jarvis.brain.config.gemini_api_key", "test-key")
        mocker.patch("jarvis.brain.config.gemini_model", "gemini-2.0-flash")
        mocker.patch("jarvis.brain.config.jarvis_persona", "You are Jarvis.")

        mock_response = MagicMock()
        mock_response.text = "Hello, sir."

        # Mock the new SDK client
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls = mocker.patch("jarvis.brain.google_genai.Client", return_value=mock_client)
        mocker.patch("jarvis.brain.genai_types.GenerateContentConfig", return_value=MagicMock())

        from jarvis.brain import GeminiProvider
        provider = GeminiProvider()
        result = await provider.generate("What is the weather?", context="No context.")
        assert result == "Hello, sir."


# ──────────────────────────────────────────────
# OpenRouterProvider
# ──────────────────────────────────────────────

class TestOpenRouterProvider:
    """Unit tests for the OpenRouterProvider class."""

    def test_init_raises_without_api_key(self, mocker):
        """OpenRouterProvider must raise ValueError when the API key is absent."""
        mocker.patch("jarvis.brain.config.openrouter_api_key", None)
        from jarvis.brain import OpenRouterProvider
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY missing"):
            OpenRouterProvider()

    def test_init_success(self, mocker):
        """OpenRouterProvider should create an AsyncOpenAI client."""
        mocker.patch("jarvis.brain.config.openrouter_api_key", "test-key")
        mock_openai_cls = mocker.patch("jarvis.brain.AsyncOpenAI")
        from jarvis.brain import OpenRouterProvider
        provider = OpenRouterProvider()
        mock_openai_cls.assert_called_once()
        assert provider is not None

    @pytest.mark.asyncio
    async def test_generate_returns_content(self, mocker):
        """generate() should return completion.choices[0].message.content."""
        mocker.patch("jarvis.brain.config.openrouter_api_key", "test-key")
        mocker.patch("jarvis.brain.config.openrouter_model", "test-model")
        mocker.patch("jarvis.brain.config.jarvis_persona", "You are Jarvis.")

        mock_message = MagicMock()
        mock_message.content = "Understood, sir."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_completion

        mock_openai_cls = mocker.patch("jarvis.brain.AsyncOpenAI")
        mock_openai_cls.return_value = mock_client

        from jarvis.brain import OpenRouterProvider
        provider = OpenRouterProvider()
        result = await provider.generate("Tell me a joke.", context="")
        assert result == "Understood, sir."


# ──────────────────────────────────────────────
# BrainManager
# ──────────────────────────────────────────────

class TestBrainManager:
    """Unit tests for BrainManager orchestration logic."""

    @pytest.fixture(autouse=True)
    def patch_heavy_deps(self, mocker):
        """Patch out Redis, tiktoken, and providers before each test."""
        mocker.patch("jarvis.brain.config.use_redis", False)
        mocker.patch("jarvis.brain.tiktoken.get_encoding")

    def test_init_without_redis(self, mocker):
        """BrainManager should default to local_history when use_redis=False."""
        from jarvis.brain import BrainManager
        manager = BrainManager()
        assert manager.redis is None
        assert manager.local_history == []

    def test_init_with_redis_success(self, mocker):
        """BrainManager should connect to Redis when use_redis=True and ping succeeds."""
        mocker.patch("jarvis.brain.config.use_redis", True)
        mocker.patch("jarvis.brain.config.redis_host", "localhost")
        mocker.patch("jarvis.brain.config.redis_port", 6379)
        mocker.patch("jarvis.brain.config.redis_db", 0)
        mock_redis_cls = mocker.patch("jarvis.brain.redis.Redis")
        mock_redis_instance = MagicMock()
        mock_redis_cls.return_value = mock_redis_instance

        from jarvis.brain import BrainManager
        manager = BrainManager()
        assert manager.redis is mock_redis_instance
        mock_redis_instance.ping.assert_called_once()

    def test_init_with_redis_failure(self, mocker, caplog):
        """BrainManager should log a warning on Redis ping failure and leave redis None."""
        import logging
        mocker.patch("jarvis.brain.config.use_redis", True)
        mocker.patch("jarvis.brain.config.redis_host", "localhost")
        mocker.patch("jarvis.brain.config.redis_port", 6379)
        mocker.patch("jarvis.brain.config.redis_db", 0)
        mock_redis_cls = mocker.patch("jarvis.brain.redis.Redis")
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Connection refused")
        mock_redis_cls.return_value = mock_redis_instance

        with caplog.at_level(logging.WARNING, logger="jarvis"):
            from jarvis.brain import BrainManager
            manager = BrainManager()
        # The warning should have been logged about the Redis failure
        assert "Redis" in caplog.text or "redis" in caplog.text.lower() or "memory" in caplog.text.lower()
        # local_history should still be initialised as fallback
        assert hasattr(manager, "local_history")

    def test_count_tokens(self, mocker):
        """_count_tokens should return the length of the encoded token list."""
        mocker.patch("jarvis.brain.config.use_redis", False)
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
        mocker.patch("jarvis.brain.tiktoken.get_encoding", return_value=mock_encoding)

        from jarvis.brain import BrainManager
        manager = BrainManager()
        count = manager._count_tokens("hello world test")
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_history_local(self, mocker):
        """_get_history should return local_history when Redis is disabled."""
        from jarvis.brain import BrainManager
        manager = BrainManager()
        manager.local_history = ["User: hi", "Assistant: hello"]
        history = await manager._get_history()
        assert history == ["User: hi", "Assistant: hello"]

    @pytest.mark.asyncio
    async def test_get_history_redis(self, mocker):
        """_get_history should fetch and deserialize from Redis when enabled."""
        mocker.patch("jarvis.brain.config.use_redis", True)
        mocker.patch("jarvis.brain.config.redis_host", "localhost")
        mocker.patch("jarvis.brain.config.redis_port", 6379)
        mocker.patch("jarvis.brain.config.redis_db", 0)

        stored_history = ["User: ping", "Assistant: pong"]
        mock_redis_cls = mocker.patch("jarvis.brain.redis.Redis")
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = json.dumps(stored_history)
        mock_redis_cls.return_value = mock_redis_instance

        from jarvis.brain import BrainManager
        manager = BrainManager()
        history = await manager._get_history()
        assert history == stored_history

    @pytest.mark.asyncio
    async def test_save_history_local_sliding_window(self, mocker):
        """_save_history should use token-aware trimming to stay within budget."""
        from jarvis.brain import BrainManager
        # Give the tokenizer a mock that returns a consistent token count per entry
        mock_encoding = MagicMock()
        # Each entry encodes to 10 tokens; budget is 1500, so all 20 fit (200 total)
        mock_encoding.encode.return_value = list(range(10))
        mocker.patch("jarvis.brain.tiktoken.get_encoding", return_value=mock_encoding)
        manager = BrainManager()
        # Supply 30 entries — all fit inside 1500 token budget (30 * 10 = 300)
        long_history = [f"msg-{i}" for i in range(30)]
        await manager._save_history(long_history)
        # All 30 should be retained since 300 < 1500
        assert len(manager.local_history) == 30

    @pytest.mark.asyncio
    async def test_generate_response_empty_question(self, mocker):
        """generate_response should return a fallback for empty input."""
        from jarvis.brain import BrainManager
        manager = BrainManager()
        result = await manager.generate_response("")
        assert result == "I didn't hear anything."

    @pytest.mark.asyncio
    async def test_generate_response_uses_provider(self, mocker):
        """generate_response should call the provider and update history."""
        mocker.patch("jarvis.brain.config.jarvis_persona", "persona")
        mocker.patch("jarvis.brain.config.gemini_api_key", "key")
        mocker.patch("jarvis.brain.config.openrouter_api_key", None)

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = "The weather is fine, sir."

        # Mock KB so it doesn't try to read from disk
        mock_kb = MagicMock()
        mock_kb.query.return_value = "some context"
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        from jarvis.brain import BrainManager
        manager = BrainManager()
        manager.provider_instances["gemini"] = mock_provider

        result = await manager.generate_response("What is the weather?")
        assert result == "The weather is fine, sir."
        mock_provider.generate.assert_called_once()
        # History should have been updated
        assert len(manager.local_history) == 2

    @pytest.mark.asyncio
    async def test_generate_response_all_providers_fail(self, mocker):
        """generate_response should return error string when all providers fail."""
        mocker.patch("jarvis.brain.config.gemini_api_key", "key")
        mocker.patch("jarvis.brain.config.openrouter_api_key", None)

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("API down")

        mock_kb = MagicMock()
        mock_kb.query.return_value = ""
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        from jarvis.brain import BrainManager
        manager = BrainManager()
        manager.provider_instances["gemini"] = mock_provider
        # Remove ollama from chain so it's only gemini
        manager.chain = ["gemini"]

        result = await manager.generate_response("test")
        assert "All modules failed" in result

    @pytest.mark.asyncio
    async def test_get_active_provider_returns_first_available(self, mocker):
        """get_active_provider should return the first provider that initializes."""
        from jarvis.brain import BrainManager
        manager = BrainManager()
        mock_provider = MagicMock()
        manager.provider_instances["gemini"] = mock_provider
        manager.chain = ["gemini", "openrouter"]

        result = await manager.get_active_provider()
        assert result is mock_provider

    @pytest.mark.asyncio
    async def test_get_active_provider_returns_none_when_empty(self, mocker):
        """get_active_provider should return None when no providers are available."""
        mocker.patch("jarvis.brain.config.gemini_api_key", None)
        mocker.patch("jarvis.brain.config.openrouter_api_key", None)

        from jarvis.brain import BrainManager
        manager = BrainManager()
        manager.chain = []  # Empty chain
        result = await manager.get_active_provider()
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_error_calls_generate_response(self, mocker):
        """analyze_error should format a prompt and call generate_response."""
        mock_kb = MagicMock()
        mock_kb.query.return_value = ""
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        from jarvis.brain import BrainManager
        manager = BrainManager()
        manager.generate_response = AsyncMock(return_value="It seems the API was down, sir.")

        result = await manager.analyze_error("open_app notepad", "FileNotFoundError")
        assert result == "It seems the API was down, sir."
        # Verify that generate_response was called with a non-empty string
        call_arg = manager.generate_response.call_args[0][0]
        assert "open_app notepad" in call_arg
        assert "FileNotFoundError" in call_arg
