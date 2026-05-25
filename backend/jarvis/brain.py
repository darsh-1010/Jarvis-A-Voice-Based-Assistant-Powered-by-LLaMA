# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Manages AI logic with async providers, sliding memory, and token tracking."""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Any

# Migrated to the new google-genai SDK (google-generativeai is deprecated)
from google import genai as google_genai
from google.genai import types as genai_types

import redis
import tiktoken
from openai import AsyncOpenAI

from jarvis.config import config
from jarvis.logger import log_action


class BaseProvider(ABC):
    """Abstract base class for async AI providers."""

    @abstractmethod
    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate a response."""


class OllamaProvider(BaseProvider):
    """Local Ollama provider (Async)."""

    def __init__(self):
        """Initialize Ollama provider with LangChain."""
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import ChatPromptTemplate
        self.model = OllamaLLM(model=config.ollama_model)
        # Structured sections + recency-effect reminder at the end improve
        # response quality and format adherence on smaller local models.
        template = (
            "{persona}\n\n"
            "[RELEVANT CONTEXT]\n{context}\n\n"
            "[USER REQUEST]\n{question}\n\n"
            "[YOUR RESPONSE — plain spoken English only, no markdown]"
        )
        self.prompt = ChatPromptTemplate.from_template(template)
        self.chain = self.prompt | self.model

    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate response via Ollama thread pool."""
        # LangChain Ollama invoke is sync, wrap it in thread
        return await asyncio.to_thread(self._invoke, question, context)

    def _invoke(self, question: str, context: str) -> str:
        """Synchronous invocation for threading."""
        return self.chain.invoke({
            "persona": config.jarvis_persona,
            "context": context if context.strip() else "No additional context.",
            "question": question
        })


class GeminiProvider(BaseProvider):
    """Google Gemini provider (Async) — uses the new google-genai SDK."""

    def __init__(self):
        """Initialize Gemini client once at construction time (not per-call)."""
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY missing")
        # FIX: Create the client ONCE here, not on every generate() call.
        # Previously, GenerativeModel was re-instantiated per call — expensive.
        self._client = google_genai.Client(api_key=config.gemini_api_key)
        self._model_id = config.gemini_model
        self._gen_config = genai_types.GenerateContentConfig(
            system_instruction=config.jarvis_persona,
            max_output_tokens=400,   # Shorter cap keeps TTS responses punchy
            temperature=0.65,         # Slightly lower for more deterministic answers
            top_p=0.9,
        )

    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate content via Gemini with system/user role separation."""
        user_turn = (
            f"[RELEVANT CONTEXT]\n{context if context.strip() else 'None'}\n\n"
            f"[USER REQUEST]\n{question}"
        )
        response = await asyncio.wait_for(
            asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model_id,
                contents=user_turn,
                config=self._gen_config,
            ),
            timeout=timeout,
        )
        return response.text


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider (Async)."""

    def __init__(self):
        """Initialize OpenRouter async client."""
        if not config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY missing")
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.openrouter_api_key
        )

    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate response via OpenRouter using proper system/user chat roles."""
        # Using the messages array with explicit system/user roles is significantly
        # more reliable than concatenating everything into a single user message.
        context_block = context.strip() if context.strip() else "No additional context."
        user_content = f"[RELEVANT CONTEXT]\n{context_block}\n\n[USER REQUEST]\n{question}"
        completion = await self.client.chat.completions.create(
            model=config.openrouter_model,
            messages=[
                {"role": "system", "content": config.jarvis_persona},
                {"role": "user", "content": user_content}
            ],
            max_tokens=400,
            temperature=0.65,
            timeout=timeout
        )
        return completion.choices[0].message.content


class BrainManager:
    """Manages AI logic with async providers, sliding memory, and token tracking."""

    # Short/casual queries that do not benefit from RAG context lookup.
    _KB_SKIP_WORDS = frozenset({
        "hello", "hi", "hey", "thanks", "thank", "you", "ok", "okay",
        "yes", "no", "bye", "goodbye", "stop", "pause", "resume",
    })
    _KB_MIN_WORDS = 5   # Skip RAG if query is fewer than this many words

    def __init__(self):
        """Initialize BrainManager with providers and Redis."""
        self.provider_instances: dict[str, Any] = {}
        self.chain = ["gemini", "openrouter", "ollama"]
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Setup Redis
        self.redis = None
        if config.use_redis:
            try:
                self.redis = redis.Redis(
                    host=config.redis_host,
                    port=config.redis_port,
                    db=config.redis_db,
                    decode_responses=True
                )
                self.redis.ping()
                log_action(
                    "BRAIN_MEMORY",
                    f"Connected to Redis at {config.redis_host}:{config.redis_port}",
                    "Connected to my long-term memory store."
                )
            except Exception as e:
                log_action(
                    "BRAIN_MEMORY",
                    f"Redis connection failed: {e}",
                    "Couldn't connect to Redis; using local memory instead.",
                    level=logging.WARNING
                )

        self.local_history: List[str] = []

        # Warm up the knowledge base at startup
        try:
            from jarvis.memory.knowledge import kb
            kb.ingest_folder(config.knowledge_dir)
        except Exception as e:
            log_action("BRAIN_KB", f"KB ingest skipped: {e}", "Knowledge base not loaded.", level=logging.WARNING)

    async def _get_history(self) -> List[str]:
        """Retrieve conversation history from Redis or local list."""
        if self.redis:
            hist = await asyncio.to_thread(self.redis.get, "jarvis_history")
            return json.loads(hist) if hist else []
        return self.local_history

    async def _save_history(self, history: List[str]):
        """
        Save conversation history with a token-aware sliding window.

        FIX: Previously used a naive count-based trim (history[-10:]) which could
        overflow the LLM context window with long responses. Now uses the tiktoken
        tokenizer to trim to a fixed token budget, ensuring prompts stay compact.
        """
        MAX_TOKENS = 1500
        trimmed: List[str] = []
        token_count = 0
        for entry in reversed(history):
            t = self._count_tokens(entry)
            if token_count + t > MAX_TOKENS:
                break
            trimmed.insert(0, entry)
            token_count += t

        if self.redis:
            await asyncio.to_thread(self.redis.set, "jarvis_history", json.dumps(trimmed))
        else:
            self.local_history = trimmed

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a string using tiktoken."""
        return len(self.tokenizer.encode(text))

    def _should_query_kb(self, question: str) -> bool:
        """
        Return True only when the query is substantive enough to benefit from RAG.

        FIX: Previously, kb.query() was called for every message including short
        greetings ('hello', 'thanks'). This wastes embedding compute and adds
        50–300ms latency with zero benefit.
        """
        words = question.lower().split()
        if len(words) < self._KB_MIN_WORDS:
            return False
        # Skip if the message is purely casual/functional words
        if all(w in self._KB_SKIP_WORDS for w in words):
            return False
        return True

    async def _get_provider(self, name: str) -> Optional[BaseProvider]:
        """Lazy-load AI provider instances."""
        if name in self.provider_instances:
            return self.provider_instances[name]
        try:
            if name == "gemini" and config.gemini_api_key:
                self.provider_instances[name] = GeminiProvider()
            elif name == "openrouter" and config.openrouter_api_key:
                self.provider_instances[name] = OpenRouterProvider()
            elif name == "ollama":
                self.provider_instances[name] = OllamaProvider()
            return self.provider_instances.get(name)
        except Exception as e:
            log_action(
                "BRAIN_INIT",
                f"Failed to initialize {name}: {e}",
                f"I had some trouble starting my {name} module.",
                level=logging.ERROR
            )
            return None

    async def get_active_provider(self) -> "BaseProvider | None":
        """
        Return the first available provider from the fallback chain.

        Used by IntentRouter to reuse provider selection without duplicating
        the chain-of-responsibility logic that lives here.
        """
        for name in self.chain:
            provider = await self._get_provider(name)
            if provider:
                return provider
        return None

    async def generate_response(self, question: str) -> str:
        """Orchestrate response generation through the provider chain."""
        if not question:
            return "I didn't hear anything."

        # FIX: Only query the knowledge base for substantive queries.
        # Greetings and short commands skip RAG entirely, saving 50–300ms.
        from jarvis.memory.knowledge import kb
        if self._should_query_kb(question):
            kb_context = await asyncio.to_thread(kb.query, question)
        else:
            kb_context = ""

        history = await self._get_history()

        # Combine KB context and conversation history
        full_context = f"KNOWLEDGE BASE:\n{kb_context}\n\nCONVERSATION HISTORY:\n" + "\n".join(history)

        last_error = ""

        for name in self.chain:
            provider = await self._get_provider(name)
            if not provider:
                continue

            try:
                start_time = time.time()
                response = await provider.generate(question, full_context)
                duration = time.time() - start_time

                # Token management
                tokens_in = self._count_tokens(question + full_context + config.jarvis_persona)
                tokens_out = self._count_tokens(response)

                log_action(
                    "BRAIN_USAGE",
                    f"Provider: {name} | In: {tokens_in} | Out: {tokens_out} | Time: {duration:.2f}s",
                    f"I've generated a response using my {name} module."
                )

                # Update history
                history.append(f"User: {question}")
                history.append(f"Assistant: {response}")
                await self._save_history(history)

                return response
            except asyncio.TimeoutError:
                log_action(
                    "BRAIN_TIMEOUT",
                    f"Provider {name} timed out",
                    f"My {name} module timed out, trying an alternative brain.",
                    level=logging.WARNING
                )
                last_error = f"{name} timed out"
                continue
            except Exception as exc:
                log_action(
                    "BRAIN_FALLBACK",
                    f"Provider {name} failed: {exc}",
                    f"My {name} module failed, trying an alternative brain.",
                    level=logging.WARNING
                )
                last_error = str(exc)
                continue

        return f"I'm sorry, sir. All modules failed. Error: {last_error}"

    async def analyze_error(self, command: str, error: str) -> str:
        """Logic for Self-Correcting Code Agent."""
        log_action(
            "BRAIN_REFLECTION",
            f"Analyzing error for: {command} | Error: {error}",
            "I'm analysing what went wrong so I can self-correct."
        )
        # Structured error analysis prompt — gives the LLM enough context to
        # diagnose the root cause and suggest an actionable fix, not just repeat the error.
        prompt = (
            "A voice command failed during execution. Analyse the root cause and give a clear, "
            "one-sentence spoken explanation of what went wrong, followed by a practical suggestion "
            "for what the user should try instead. Be direct and calm. No markdown.\n\n"
            f"Failed command: '{command}'\n"
            f"Error details: '{error}'"
        )
        return await self.generate_response(prompt)
