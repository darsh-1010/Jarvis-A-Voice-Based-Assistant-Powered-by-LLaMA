"""AI Brain for Jarvis with Redis memory, token management, and persona support."""
import time
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Any
import google.generativeai as genai
from openai import OpenAI
import tiktoken
import redis
from jarvis.config import (
    OLLAMA_MODEL, GEMINI_MODEL, OPENROUTER_MODEL,
    GEMINI_API_KEY, OPENROUTER_API_KEY,
    REDIS_HOST, REDIS_PORT, REDIS_DB, USE_REDIS
)
from jarvis.settings_manager import settings_manager
from jarvis.logger import logger


class BaseProvider(ABC):
    """Abstract base class for AI providers."""
    @abstractmethod
    def generate(self, question: str, context: str, timeout: int = 10) -> str:
        """Generate a response."""

class OllamaProvider(BaseProvider):
    """Local Ollama provider."""
    def __init__(self):
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import ChatPromptTemplate
        self.model = OllamaLLM(model=OLLAMA_MODEL)
        template = "{persona}\nContext: {context}\nQuestion: {question}\nAnswer:"
        self.prompt = ChatPromptTemplate.from_template(template)
        self.chain = self.prompt | self.model

    def generate(self, question: str, context: str, timeout: int = 10) -> str:
        return self.chain.invoke({
            "persona": settings_manager.get("persona"),
            "context": context, 
            "question": question
        })


class GeminiProvider(BaseProvider):
    """Google Gemini provider."""
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY missing")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def generate(self, question: str, context: str, timeout: int = 10) -> str:
        persona = settings_manager.get("persona")
        full_prompt = f"{persona}\nContext: {context}\nQuestion: {question}\nAnswer:"
        response = self.model.generate_content(
            full_prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.7}
        )
        return response.text


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider."""
    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY missing")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY
        )

    def generate(self, question: str, context: str, timeout: int = 10) -> str:
        persona = settings_manager.get("persona")
        full_prompt = f"{persona}\nContext: {context}\nQuestion: {question}"
        completion = self.client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=512,
            timeout=timeout
        )
        return completion.choices[0].message.content


class BrainManager:
    """Manages AI logic with Redis memory and token tracking."""

    def __init__(self):
        self.provider_instances: dict[str, Any] = {}
        self.chain = ["gemini", "openrouter", "ollama"]
        self.tokenizer = tiktoken.get_encoding("cl100k_base") # Standard for GPT-4/Gemini
        
        # Setup Redis
        self.redis = None
        if USE_REDIS:
            try:
                self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
                self.redis.ping()
                logger.info("[BRAIN_MEMORY] Connected to Redis.")
            except Exception as e:
                logger.warning(f"[BRAIN_MEMORY] Redis failed: {e}. Falling back to local.")
        
        self.local_history: List[str] = []

    def _get_history(self) -> List[str]:
        if self.redis:
            hist = self.redis.get("jarvis_history")
            return json.loads(hist) if hist else []
        return self.local_history

    def _save_history(self, history: List[str]):
        if self.redis:
            self.redis.set("jarvis_history", json.dumps(history[-10:]))
        else:
            self.local_history = history[-10:]

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _get_provider(self, name: str) -> Optional[BaseProvider]:
        if name in self.provider_instances:
            return self.provider_instances[name]
        try:
            if name == "gemini" and GEMINI_API_KEY:
                self.provider_instances[name] = GeminiProvider()
            elif name == "openrouter" and OPENROUTER_API_KEY:
                self.provider_instances[name] = OpenRouterProvider()
            elif name == "ollama":
                self.provider_instances[name] = OllamaProvider()
            return self.provider_instances.get(name)
        except Exception as e:
            logger.error(f"[BRAIN_INIT] Failed {name}: {e}")
            return None

    def generate_response(self, question: str) -> str:
        if not question:
            return "I didn't hear anything."

        history = self._get_history()
        context = "\n".join(history)
        last_error = ""

        for name in self.chain:
            provider = self._get_provider(name)
            if not provider: continue

            try:
                start_time = time.time()
                response = provider.generate(question, context)
                duration = time.time() - start_time
                
                # Token management
                tokens_in = self._count_tokens(question + context + JARVIS_PERSONA)
                tokens_out = self._count_tokens(response)
                
                logger.info(f"[BRAIN_USAGE] Provider: {name} | In: {tokens_in} | Out: {tokens_out} | Time: {duration:.2f}s")
                
                # Update history
                history.append(f"User: {question}")
                history.append(f"Assistant: {response}")
                self._save_history(history)
                
                return response
            except Exception as exc:
                logger.warning(f"[BRAIN_FALLBACK] {name} failed: {exc}")
                last_error = str(exc)
                continue

        return f"I'm sorry, sir. All modules failed. Error: {last_error}"

    def analyze_error(self, command: str, error: str) -> str:
        """Logic for Self-Correcting Code Agent (Pillar 5.1)."""
        logger.info(f"[BRAIN_REFLECTION] Analyzing error for: {command}")
        prompt = (
            f"The following command failed: '{command}'\n"
            f"Error message: '{error}'\n"
            "Analyze the error and provide a corrected command or a brief explanation of how to fix it."
        )
        return self.generate_response(prompt)
