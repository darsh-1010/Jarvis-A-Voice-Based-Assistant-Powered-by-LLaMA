# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""LLM-powered intent router that maps natural-language commands to registered tools."""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from jarvis.logger import log_action


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────


@dataclass
class IntentResult:
    """Encapsulates the LLM's routing decision for a command."""

    tool_name: Optional[str]
    # Keyword arguments to pass directly into registry.invoke()
    params: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
# Prompt Builder
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an intent classifier for a voice assistant. "
    "Given a user command and a list of available tools, decide which tool to call. "
    "Respond with ONLY a valid JSON object — no markdown, no explanation. "
    'Format: {"tool": "<tool_name_or_null>", "params": {...}} '
    "Use null for tool if the request is conversational and no tool fits."
)

_NEWS_CATEGORIES = {
    "technology",
    "business",
    "health",
    "sports",
    "entertainment",
    "science",
    "general",
}

# Redis cache TTL for intent results (1 hour)
_INTENT_CACHE_TTL = 3600


def _build_classification_prompt(command: str, tools: list) -> str:
    """
    Build a deterministic JSON-classification prompt from the tool manifest.

    The prompt lists every tool with its description and known parameter hints
    so the LLM can map natural language to the correct tool and extract args.
    """
    # Compact tool listing — keeps token count low while remaining unambiguous
    tool_lines = []
    for tool in tools:
        tool_lines.append(f"- {tool['name']}: {tool['description']}")

    tool_manifest = "\n".join(tool_lines)

    # Inline parameter hints reduce hallucination on argument extraction
    param_notes = (
        "Parameter hints:\n"
        f"  fetch_latest_news     -> category (one of: {', '.join(sorted(_NEWS_CATEGORIES))}, default: general)\n"
        "  open_app              -> app_name (e.g. notepad, calculator, cmd)\n"
        "  search_google         -> query (the search phrase)\n"
        "  search_youtube        -> query (the search phrase)\n"
        "  search_spotify_web    -> song_name (search on Spotify web player)\n"
        "  get_weather           -> city (city name, optional — defaults to configured city)\n"
        "  get_forecast          -> city (city name, optional)\n"
        "  get_crypto_price      -> coin (e.g. bitcoin, ethereum, solana — name or ticker)\n"
        "  get_stock_price       -> symbol (ticker symbol, e.g. AAPL, RELIANCE.BSE)\n"
        "  get_stock_history     -> symbol (ticker), period (e.g. 5d, 1mo, 3mo, default: 5d)\n"
        "  spotify_play          -> song_name (song or artist to search and play)\n"
        "  start_pomodoro        -> minutes (integer, default: 25)\n"
        "  translate_text        -> text (phrase to translate), "
        "target_language (ISO code or name, e.g. fr, french, ja)\n"
        "  list_calendar_events  -> max_results (integer, default: 5)\n"
        "  create_calendar_event -> title (event name), date (YYYY-MM-DD), "
        "start_time (HH:MM), duration_hours (int, default: 1)\n"
        "  read_inbox            -> max_results (integer, default: 5)\n"
        "  send_email            -> to (email address), subject (string), body (message text)\n"
        "  list_processes        -> top_n (integer, default: 5)\n"
        "  kill_process          -> process_name (partial or full process name)\n"
    )

    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Available tools:\n{tool_manifest}\n\n"
        f"{param_notes}\n"
        f'User command: "{command}"\n\n'
        "JSON response:"
    )


# ──────────────────────────────────────────────
# Intent Router
# ──────────────────────────────────────────────


class IntentRouter:
    """
    Routes a natural-language command to the best-matching registered tool.

    Uses the active LLM provider from BrainManager to classify the intent
    and extract parameters, then returns an IntentResult. Falls back
    gracefully on any parse error so the assistant always has a response path.

    OPTIMIZATION: Results are cached in Redis by MD5 hash of the command.
    Identical or repeat commands are served in <10ms instead of ~1-2s LLM
    round-trips. Cache TTL is 1 hour.
    """

    # Max time to wait for LLM classification before giving up
    _CLASSIFY_TIMEOUT = 8.0

    def __init__(self, brain_manager) -> None:
        """
        Initialise with a reference to the BrainManager.

        Args:
            brain_manager: The active BrainManager instance (provides LLM access).
        """
        self._brain = brain_manager
        log_action(
            "INTENT_INIT",
            "IntentRouter attached to BrainManager.",
            "My intent routing module is ready.",
        )

    def _cache_key(self, command: str) -> str:
        """Generate a stable Redis cache key for a command."""
        digest = hashlib.md5(
            command.lower().strip().encode(), usedforsecurity=False
        ).hexdigest()
        return f"intent:{digest}"

    async def classify(self, command: str, tools: list) -> IntentResult:
        """
        Ask the LLM which tool (if any) matches the command and extract its params.

        FIX: Added Redis-backed intent caching. Repeat or similar exact commands
        now return in <10ms from cache rather than triggering a new LLM call.

        Args:
            command: The raw natural-language command from the user.
            tools:   List of tool dicts from registry.list_tools()

        Returns:
            IntentResult with tool_name=None if no tool matches.
        """
        if not command or not tools:
            return IntentResult(tool_name=None)

        known_names = {t["name"] for t in tools}

        # 1. Check Redis cache first (exact-match on normalized command)
        cached = await self._get_cached_intent(command)
        if cached is not None:
            log_action(
                "INTENT_CACHE_HIT",
                f"Cache hit for: '{command[:60]}'",
                "Routing from cached intent — no LLM call needed.",
            )
            # Validate cached tool still exists in current registry
            if cached.tool_name is None or cached.tool_name in known_names:
                return cached

        # 2. Classify via LLM with a hard timeout
        prompt = _build_classification_prompt(command, tools)
        try:
            raw_response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self._CLASSIFY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            log_action(
                "INTENT_TIMEOUT",
                f"Classification timed out after {self._CLASSIFY_TIMEOUT}s",
                "Intent classification timed out; falling back to conversation.",
                level=logging.WARNING,
            )
            return IntentResult(tool_name=None)

        if not raw_response:
            return IntentResult(tool_name=None)

        result = self._parse_response(raw_response, known_names)

        # 3. Cache successful intent results (only cache tool matches, not None)
        if result.tool_name:
            await self._cache_intent(command, result)

        return result

    async def _get_cached_intent(self, command: str) -> Optional[IntentResult]:
        """Return a cached IntentResult if available, else None."""
        if not self._brain.redis:
            return None
        try:
            raw = await asyncio.to_thread(
                self._brain.redis.get, self._cache_key(command)
            )
            if raw:
                data = json.loads(raw)
                return IntentResult(
                    tool_name=data.get("tool_name"), params=data.get("params", {})
                )
        except Exception as exc:
            log_action(
                "INTENT_CACHE_ERR", f"Cache read error: {exc}", "", level=logging.DEBUG
            )
        return None

    async def _cache_intent(self, command: str, result: IntentResult) -> None:
        """Store an IntentResult in Redis with TTL."""
        if not self._brain.redis:
            return
        try:
            payload = json.dumps(
                {"tool_name": result.tool_name, "params": result.params}
            )
            await asyncio.to_thread(
                self._brain.redis.setex,
                self._cache_key(command),
                _INTENT_CACHE_TTL,
                payload,
            )
        except Exception as exc:
            log_action(
                "INTENT_CACHE_ERR", f"Cache write error: {exc}", "", level=logging.DEBUG
            )

    async def _call_llm(self, prompt: str) -> str:
        """
        Generate a response through the provider chain and return the raw text.

        Uses get_active_provider() to reuse the same fallback chain as brain.py
        without duplicating provider selection logic.
        """
        provider = await self._brain.get_active_provider()
        if not provider:
            log_action(
                "INTENT_NO_PROVIDER",
                "No LLM provider available for intent classification.",
                "I couldn't reach my classification module.",
                level=logging.WARNING,
            )
            return ""

        try:
            # Empty context — the prompt is self-contained
            return await provider.generate(prompt, context="")
        except Exception as exc:
            log_action(
                "INTENT_LLM_FAIL",
                f"LLM call failed during intent classification: {exc}",
                "I had trouble deciding which action to take.",
                level=logging.WARNING,
            )
            return ""

    def _parse_response(self, raw: str, known_names: set) -> IntentResult:
        """
        Parse the LLM's JSON response into an IntentResult.

        Strips any markdown code fences the model may emit, then validates
        that the returned tool name exists in the registry. Returns
        IntentResult(tool_name=None) on any parse or validation failure.
        """
        # Strip markdown fences that some models include despite instructions
        cleaned = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            log_action(
                "INTENT_PARSE_FAIL",
                f"JSON decode error: {exc} | Raw: {cleaned[:120]}",
                "I couldn't parse the routing decision; falling back to conversation.",
                level=logging.WARNING,
            )
            return IntentResult(tool_name=None)

        tool_name = payload.get("tool")
        params = payload.get("params", {})

        # Validate: null / "null" / unknown name all map to conversational fallback
        if not tool_name or tool_name == "null" or tool_name not in known_names:
            log_action(
                "INTENT_NO_MATCH",
                f"No tool matched for command. LLM returned: tool={tool_name}",
                "No specific tool matched; routing to conversational brain.",
            )
            return IntentResult(tool_name=None)

        # Ensure params is always a dict (guard against unexpected model output)
        if not isinstance(params, dict):
            params = {}

        log_action(
            "INTENT_MATCHED",
            f"Tool: {tool_name} | Params: {params}",
            f"I've decided to use the '{tool_name.replace('_', ' ')}' capability.",
        )
        return IntentResult(tool_name=tool_name, params=params)
