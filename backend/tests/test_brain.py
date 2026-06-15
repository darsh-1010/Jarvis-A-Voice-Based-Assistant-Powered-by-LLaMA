# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Tests for jarvis/brain.py — BrainManager and LiteLLM Router integration."""

import json
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import pytest

from jarvis.brain import BrainManager, LiteLLMProviderWrapper


class TestBrainManager:
    """Unit tests for BrainManager orchestration logic."""

    @pytest.fixture(autouse=True)
    def patch_heavy_deps(self, mocker: Any) -> None:
        """Patch out Redis, tiktoken, and Router before each test."""
        mocker.patch("jarvis.brain.config.use_redis", False)
        mocker.patch("jarvis.brain.tiktoken.get_encoding")

    def test_init_without_redis(self) -> None:
        """BrainManager should default to local_history when use_redis=False."""
        manager = BrainManager()
        assert manager.redis is None
        assert manager.local_history == []

    def test_init_with_redis_success(self, mocker: Any) -> None:
        """BrainManager should connect to Redis when use_redis=True and ping succeeds."""
        mocker.patch("jarvis.brain.config.use_redis", True)
        mocker.patch("jarvis.brain.config.redis_host", "localhost")
        mocker.patch("jarvis.brain.config.redis_port", 6379)
        mocker.patch("jarvis.brain.config.redis_db", 0)
        mock_redis_cls = mocker.patch("jarvis.brain.redis.Redis")
        mock_redis_instance = MagicMock()
        mock_redis_cls.return_value = mock_redis_instance

        manager = BrainManager()
        assert manager.redis is mock_redis_instance
        mock_redis_instance.ping.assert_called_once()

    def test_init_with_redis_failure(self, mocker: Any, caplog: Any) -> None:
        """BrainManager should log a warning on Redis ping failure and leave redis None."""
        mocker.patch("jarvis.brain.config.use_redis", True)
        mocker.patch("jarvis.brain.config.redis_host", "localhost")
        mocker.patch("jarvis.brain.config.redis_port", 6379)
        mocker.patch("jarvis.brain.config.redis_db", 0)
        mock_redis_cls = mocker.patch("jarvis.brain.redis.Redis")
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Connection refused")
        mock_redis_cls.return_value = mock_redis_instance

        with caplog.at_level(logging.WARNING, logger="jarvis"):
            manager = BrainManager()
        assert "Redis" in caplog.text or "redis" in caplog.text.lower() or "memory" in caplog.text.lower()
        assert hasattr(manager, "local_history")

    def test_init_router_model_list(self, mocker: Any) -> None:
        """Router should be initialized with Gemini, Groq, and Ollama when keys are present."""
        mocker.patch("jarvis.brain.config.gemini_api_key", "gemini-key")
        mocker.patch("jarvis.brain.config.groq_api_key", "groq-key")
        mocker.patch("jarvis.brain.config.gemini_model", "gemini-2.0-flash")
        mocker.patch("jarvis.brain.config.groq_model", "llama-3.3-70b-versatile")
        mocker.patch("jarvis.brain.config.ollama_model", "gemma2:2b")

        manager = BrainManager()
        models = manager.router.model_list
        assert len(models) == 3
        assert models[0]["litellm_params"]["model"] == "gemini/gemini-2.0-flash"
        assert models[0]["litellm_params"]["api_key"] == "gemini-key"
        assert models[1]["litellm_params"]["model"] == "groq/llama-3.3-70b-versatile"
        assert models[1]["litellm_params"]["api_key"] == "groq-key"
        assert models[2]["litellm_params"]["model"] == "ollama/gemma2:2b"

    def test_init_router_model_list_missing_keys(self, mocker: Any) -> None:
        """Router should skip Gemini if its key is absent, but still include Groq and Ollama."""
        mocker.patch("jarvis.brain.config.gemini_api_key", None)
        mocker.patch("jarvis.brain.config.groq_api_key", "groq-key")
        mocker.patch("jarvis.brain.config.groq_model", "llama-3.3-70b-versatile")
        mocker.patch("jarvis.brain.config.ollama_model", "gemma2:2b")

        manager = BrainManager()
        models = manager.router.model_list
        assert len(models) == 2
        assert models[0]["litellm_params"]["model"] == "groq/llama-3.3-70b-versatile"
        assert models[1]["litellm_params"]["model"] == "ollama/gemma2:2b"

    def test_count_tokens(self, mocker: Any) -> None:
        """_count_tokens should return the length of the encoded token list."""
        mocker.patch("jarvis.brain.config.use_redis", False)
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
        mocker.patch("jarvis.brain.tiktoken.get_encoding", return_value=mock_encoding)

        manager = BrainManager()
        count_tokens_func = getattr(manager, "_count_tokens")
        count = count_tokens_func("hello world test")
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_history_local(self) -> None:
        """_get_history should return local_history when Redis is disabled."""
        manager = BrainManager()
        manager.local_history = ["User: hi", "Assistant: hello"]
        get_history_func = getattr(manager, "_get_history")
        history = await get_history_func()
        assert history == ["User: hi", "Assistant: hello"]

    @pytest.mark.asyncio
    async def test_get_history_redis(self, mocker: Any) -> None:
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

        manager = BrainManager()
        get_history_func = getattr(manager, "_get_history")
        history = await get_history_func()
        assert history == stored_history

    @pytest.mark.asyncio
    async def test_save_history_local_sliding_window(self, mocker: Any) -> None:
        """_save_history should use token-aware trimming to stay within budget."""
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = list(range(10))
        mocker.patch("jarvis.brain.tiktoken.get_encoding", return_value=mock_encoding)
        manager = BrainManager()
        long_history = [f"msg-{i}" for i in range(30)]
        save_history_func = getattr(manager, "_save_history")
        await save_history_func(long_history)
        assert len(manager.local_history) == 30

    @pytest.mark.asyncio
    async def test_generate_response_empty_question(self) -> None:
        """generate_response should return a fallback for empty input."""
        manager = BrainManager()
        result = await manager.generate_response("")
        assert result == "I didn't hear anything."

    @pytest.mark.asyncio
    async def test_generate_response_uses_provider(self, mocker: Any) -> None:
        """generate_response should call the router.acompletion and update history."""
        mocker.patch("jarvis.brain.config.jarvis_persona", "persona")
        mocker.patch("jarvis.brain.config.gemini_api_key", "key")

        mock_choice = MagicMock()
        mock_choice.message.content = "The weather is fine, sir."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gemini/gemini-2.0-flash"

        mock_acompletion = mocker.patch("jarvis.brain.Router.acompletion", new_callable=AsyncMock)
        mock_acompletion.return_value = mock_response

        mock_kb = MagicMock()
        mock_kb.query.return_value = "some context"
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        manager = BrainManager()

        result = await manager.generate_response("What is the weather?")
        assert result == "The weather is fine, sir."
        mock_acompletion.assert_called_once()
        assert len(manager.local_history) == 2

    @pytest.mark.asyncio
    async def test_generate_response_all_providers_fail(self, mocker: Any) -> None:
        """generate_response should return error string when router.acompletion fails."""
        mock_acompletion = mocker.patch("jarvis.brain.Router.acompletion", new_callable=AsyncMock)
        mock_acompletion.side_effect = Exception("All models failed")

        mock_kb = MagicMock()
        mock_kb.query.return_value = ""
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        manager = BrainManager()

        result = await manager.generate_response("test")
        assert "All modules failed" in result

    @pytest.mark.asyncio
    async def test_get_active_provider_returns_wrapper(self) -> None:
        """get_active_provider should return LiteLLMProviderWrapper wrapping the router."""
        manager = BrainManager()
        provider = await manager.get_active_provider()
        assert isinstance(provider, LiteLLMProviderWrapper)
        assert provider is not None
        assert provider.router is manager.router

    @pytest.mark.asyncio
    async def test_get_active_provider_returns_none_when_empty(self) -> None:
        """get_active_provider should return None when router model list is empty."""
        manager = BrainManager()
        manager.router.model_list = []
        result = await manager.get_active_provider()
        assert result is None

    @pytest.mark.asyncio
    async def test_provider_wrapper_generate(self, mocker: Any) -> None:
        """LiteLLMProviderWrapper.generate should call router.acompletion with system prompt and user request."""
        mock_choice = MagicMock()
        mock_choice.message.content = "wrapper response"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_acompletion = mocker.patch("jarvis.brain.Router.acompletion", new_callable=AsyncMock)
        mock_acompletion.return_value = mock_response

        manager = BrainManager()
        provider = await manager.get_active_provider()
        assert provider is not None

        result = await provider.generate("hello", "context text", timeout=15)
        assert result == "wrapper response"
        mock_acompletion.assert_called_once()
        called_kwargs = mock_acompletion.call_args[1]
        assert called_kwargs["model"] == "jarvis-default"
        assert called_kwargs["timeout"] == 15
        assert len(called_kwargs["messages"]) == 2
        assert called_kwargs["messages"][0]["role"] == "system"
        assert called_kwargs["messages"][1]["role"] == "user"
        assert "context text" in called_kwargs["messages"][1]["content"]
        assert "hello" in called_kwargs["messages"][1]["content"]

    @pytest.mark.asyncio
    async def test_analyze_error_calls_generate_response(self, mocker: Any) -> None:
        """analyze_error should format a prompt and call generate_response."""
        mock_kb = MagicMock()
        mock_kb.query.return_value = ""
        mocker.patch("jarvis.memory.knowledge.kb", mock_kb)

        manager = BrainManager()
        manager.generate_response = AsyncMock(return_value="It seems the API was down, sir.")

        result = await manager.analyze_error("open_app notepad", "FileNotFoundError")
        assert result == "It seems the API was down, sir."
        call_arg = manager.generate_response.call_args[0][0]
        assert "open_app notepad" in call_arg
        assert "FileNotFoundError" in call_arg
