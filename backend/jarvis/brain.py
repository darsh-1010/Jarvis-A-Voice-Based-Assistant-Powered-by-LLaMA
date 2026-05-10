# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Manages AI logic with async providers, sliding memory, and token tracking."""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Any

import google.generativeai as genai
import httpx
import redis
import tiktoken
from openai import AsyncOpenAI

from jarvis.config import config
from jarvis.logger import logger, log_action


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
        template = "{persona}\nContext: {context}\nQuestion: {question}\nAnswer:"
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
            "context": context,
            "question": question
        })


class GeminiProvider(BaseProvider):
    """Google Gemini provider (Async)."""

    def __init__(self):
        """Initialize Gemini model with API key."""
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY missing")
        genai.configure(api_key=config.gemini_api_key)
        self.model = genai.GenerativeModel(config.gemini_model)

    async def generate(self, question: str, context: str, timeout: int = 20) -> str:
        """Generate content via Gemini thread pool."""
        full_prompt = f"{config.jarvis_persona}\nContext: {context}\nQuestion: {question}\nAnswer:"
        # Gemini SDK generate_content is blocking, use thread or async method if available
        response = await asyncio.to_thread(
            self.model.generate_content,
            full_prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.7}
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
        """Generate response via OpenRouter."""
        full_prompt = f"{config.jarvis_persona}\nContext: {context}\nQuestion: {question}"
        completion = await self.client.chat.completions.create(
            model=config.openrouter_model,
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=512,
            timeout=timeout
        )
        return completion.choices[0].message.content


class BrainManager:
    """Manages AI logic with async providers, sliding memory, and token tracking."""

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

    async def _get_history(self) -> List[str]:
        """Retrieve conversation history from Redis or local list."""
        if self.redis:
            hist = await asyncio.to_thread(self.redis.get, "jarvis_history")
            return json.loads(hist) if hist else []
        return self.local_history

    async def _save_history(self, history: List[str]):
        """Save conversation history with a sliding window."""
        # Sliding window: keep roughly 2000 tokens
        trimmed_history = history[-10:]  # Basic implementation for now
        if self.redis:
            await asyncio.to_thread(self.redis.set, "jarvis_history", json.dumps(trimmed_history))
        else:
            self.local_history = trimmed_history

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a string using tiktoken."""
        return len(self.tokenizer.encode(text))

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

    async def generate_response(self, question: str) -> str:
        """Orchestrate response generation through the provider chain."""
        if not question:
            return "I didn't hear anything."

        # RAG: Search for relevant context
        from jarvis.memory.knowledge import kb
        kb_context = await asyncio.to_thread(kb.query, question)

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
            "I'm analyzing what went wrong so I can self-correct."
        )
        prompt = (
            f"The following command failed: '{command}'\n"
            f"Error message: '{error}'\n"
            "Analyze the error and provide a brief explanation or fix."
        )
        return await self.generate_response(prompt)

