# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Manages AI logic with LiteLLM Router, sliding memory, and token tracking."""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Any

import redis
import tiktoken
from litellm.router import Router

from jarvis.config import config
from jarvis.logger import log_action


class BaseProvider(ABC):
    """Abstract base class for async AI providers."""

    @abstractmethod
    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate a response."""


class LiteLLMProviderWrapper(BaseProvider):
    """Wrapper that adapts LiteLLM Router to the legacy BaseProvider interface."""

    def __init__(self, router: Router):
        """Initialize the provider wrapper with a LiteLLM Router."""
        self.router = router

    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate a response using the LiteLLM Router."""
        context_block = context.strip() if context.strip() else "No additional context."
        user_content = f"[RELEVANT CONTEXT]\n{context_block}\n\n[USER REQUEST]\n{question}"
        messages: List[Any] = [
            {"role": "system", "content": config.jarvis_persona},
            {"role": "user", "content": user_content},
        ]
        response = await self.router.acompletion(
            model="jarvis-default",
            messages=messages,
            timeout=timeout,
        )
        if response and response.choices:
            return response.choices[0].message.content or ""
        return ""


class BrainManager:
    """Manages AI logic with LiteLLM Router, sliding memory, and token tracking."""

    # Short/casual queries that do not benefit from RAG context lookup.
    _KB_SKIP_WORDS = frozenset(
        {
            "hello",
            "hi",
            "hey",
            "thanks",
            "thank",
            "you",
            "ok",
            "okay",
            "yes",
            "no",
            "bye",
            "goodbye",
            "stop",
            "pause",
            "resume",
        }
    )
    _KB_MIN_WORDS = 5  # Skip RAG if query is fewer than this many words

    def __init__(self):
        """Initialize BrainManager with LiteLLM Router and Redis."""
        model_list = []
        if config.gemini_api_key:
            model_list.append(
                {
                    "model_name": "jarvis-default",
                    "litellm_params": {
                        "model": f"gemini/{config.gemini_model}",
                        "api_key": config.gemini_api_key,
                        "temperature": 0.65,
                        "max_tokens": 400,
                    },
                }
            )
        if config.groq_api_key:
            model_list.append(
                {
                    "model_name": "jarvis-default",
                    "litellm_params": {
                        "model": f"groq/{config.groq_model}",
                        "api_key": config.groq_api_key,
                        "temperature": 0.65,
                        "max_tokens": 400,
                    },
                }
            )
        # Always append local Ollama as a reliable offline safety net
        model_list.append(
            {
                "model_name": "jarvis-default",
                "litellm_params": {
                    "model": f"ollama/{config.ollama_model}",
                    "api_base": "http://localhost:11434",
                },
            }
        )

        self.router = Router(model_list=model_list)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Setup Redis
        self.redis = None
        if config.use_redis:
            try:
                self.redis = redis.Redis(
                    host=config.redis_host,
                    port=config.redis_port,
                    db=config.redis_db,
                    decode_responses=True,
                )
                self.redis.ping()
                log_action(
                    "BRAIN_MEMORY",
                    f"Connected to Redis at {config.redis_host}:{config.redis_port}",
                    "Connected to my long-term memory store.",
                )
            except Exception as e:
                log_action(
                    "BRAIN_MEMORY",
                    f"Redis connection failed: {e}",
                    "Couldn't connect to Redis; using local memory instead.",
                    level=logging.WARNING,
                )

        self.local_history: List[str] = []
        # Telemetry store injected after construction via set_telemetry_store().
        self._telemetry: Optional[Any] = None

        # Warm up the knowledge base at startup
        try:
            from jarvis.memory.knowledge import kb

            kb.ingest_folder(config.knowledge_dir)
        except Exception as e:
            log_action(
                "BRAIN_KB",
                f"KB ingest skipped: {e}",
                "Knowledge base not loaded.",
                level=logging.WARNING,
            )

    async def _get_history(self) -> List[str]:
        """Retrieve conversation history from Redis or local list."""
        if self.redis:
            hist = await asyncio.to_thread(self.redis.get, "jarvis_history")
            if isinstance(hist, (str, bytes, bytearray)):
                return json.loads(hist)
            return []
        return self.local_history

    async def _save_history(self, history: List[str]):
        """Save conversation history with a token-aware sliding window."""
        max_tokens = 1500
        trimmed: List[str] = []
        token_count = 0
        for entry in reversed(history):
            t = self._count_tokens(entry)
            if token_count + t > max_tokens:
                break
            trimmed.insert(0, entry)
            token_count += t

        if self.redis:
            await asyncio.to_thread(
                self.redis.set, "jarvis_history", json.dumps(trimmed)
            )
        else:
            self.local_history = trimmed

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a string using tiktoken."""
        return len(self.tokenizer.encode(text))

    def _should_query_kb(self, question: str) -> bool:
        """Return True only when the query is substantive enough to benefit from RAG."""
        words = question.lower().split()
        if len(words) < self._KB_MIN_WORDS:
            return False
        # Skip if the message is purely casual/functional words
        if all(w in self._KB_SKIP_WORDS for w in words):
            return False
        return True

    async def get_active_provider(self) -> Optional[BaseProvider]:
        """Return a LiteLLMProviderWrapper wrapping the router, matching BaseProvider interface."""
        if not self.router.model_list:
            return None
        return LiteLLMProviderWrapper(self.router)

    async def _prepare_payload(self, question: str) -> tuple[List[Any], str, List[str]]:
        """Query knowledge base and retrieve history to build the model payload."""
        from jarvis.memory.knowledge import kb

        if self._should_query_kb(question):
            kb_context = await asyncio.to_thread(kb.query, question)
        else:
            kb_context = ""

        history = await self._get_history()
        full_context = (
            f"KNOWLEDGE BASE:\n{kb_context}\n\nCONVERSATION HISTORY:\n"
            + "\n".join(history)
        )
        context_block = full_context.strip() if full_context.strip() else "No additional context."
        user_content = f"[RELEVANT CONTEXT]\n{context_block}\n\n[USER REQUEST]\n{question}"
        messages: List[Any] = [
            {"role": "system", "content": config.jarvis_persona},
            {"role": "user", "content": user_content},
        ]
        return messages, full_context, history

    async def generate_response(self, question: str) -> str:
        """Orchestrate response generation through the LiteLLM Router."""
        if not question:
            return "I didn't hear anything."

        messages, full_context, history = await self._prepare_payload(question)

        try:
            start_time = time.time()
            response = await self.router.acompletion(
                model="jarvis-default",
                messages=messages,
            )
            duration = time.time() - start_time

            response_text = response.choices[0].message.content or ""
            model_used = response.model or "unknown"

            # Token management
            tokens_in = self._count_tokens(
                question + full_context + config.jarvis_persona
            )
            tokens_out = self._count_tokens(response_text)

            log_action(
                "BRAIN_USAGE",
                f"Provider: {model_used} | In: {tokens_in} | Out: {tokens_out} | Time: {duration:.2f}s",
                f"I've generated a response using my {model_used} module.",
            )

            # Update history
            history.append(f"User: {question}")
            history.append(f"Assistant: {response_text}")
            await self._save_history(history)

            return response_text
        except Exception as exc:
            log_action(
                "BRAIN_FALLBACK",
                f"LiteLLM router failed: {exc}",
                "My generative module failed, trying to recover.",
                level=logging.ERROR,
            )
            return f"I'm sorry, sir. All modules failed. Error: {exc}"

    async def analyze_error(self, command: str, error: str) -> str:
        """Logic for Self-Correcting Code Agent."""
        log_action(
            "BRAIN_REFLECTION",
            f"Analyzing error for: {command} | Error: {error}",
            "I'm analysing what went wrong so I can self-correct.",
        )
        prompt = (
            "A voice command failed during execution. Analyse the root cause and give a clear, "
            "one-sentence spoken explanation of what went wrong, followed by a practical suggestion "
            "for what the user should try instead. Be direct and calm. No markdown.\n\n"
            f"Failed command: '{command}'\n"
            f"Error details: '{error}'"
        )
        return await self.generate_response(prompt)

    def set_telemetry_store(self, store: Any) -> None:
        """Inject the TelemetryStore for performance reporting."""
        self._telemetry = store

    async def get_performance_summary(self) -> List[dict]:
        """Return per-tool aggregated failure stats for the /memory/stats endpoint."""
        if self._telemetry is None:
            return []
        return await self._telemetry.get_failure_stats()
