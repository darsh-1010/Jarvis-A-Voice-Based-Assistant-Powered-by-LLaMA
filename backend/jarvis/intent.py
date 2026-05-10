# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""LLM-powered intent router that maps natural-language commands to registered tools."""
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
    "Format: {{\"tool\": \"<tool_name_or_null>\", \"params\": {{...}}}} "
    "Use null for tool if the request is conversational and no tool fits."
)

_NEWS_CATEGORIES = {"technology", "business", "health", "sports", "entertainment", "science", "general"}


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
        f"  fetch_latest_news -> category (one of: {', '.join(sorted(_NEWS_CATEGORIES))}, default: general)\n"
        "  open_app          -> app_name (e.g. notepad, calculator, cmd)\n"
        "  search_google     -> query (the search phrase)\n"
        "  search_youtube    -> query (the search phrase)\n"
        "  open_spotify      -> song_name (name of song or artist)\n"
    )

    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Available tools:\n{tool_manifest}\n\n"
        f"{param_notes}\n"
        f"User command: \"{command}\"\n\n"
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
    """

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
            "My intent routing module is ready."
        )

    async def classify(self, command: str, tools: list) -> IntentResult:
        """
        Ask the LLM which tool (if any) matches the command and extract its params.

        Args:
            command: The raw natural-language command from the user.
            tools:   List of tool dicts from registry.list_tools().

        Returns:
            IntentResult with tool_name=None if no tool matches.
        """
        if not command or not tools:
            return IntentResult(tool_name=None)

        prompt = _build_classification_prompt(command, tools)
        known_names = {t["name"] for t in tools}

        raw_response = await self._call_llm(prompt)
        if not raw_response:
            return IntentResult(tool_name=None)

        return self._parse_response(raw_response, known_names)

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
                level=logging.WARNING
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
                level=logging.WARNING
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
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            log_action(
                "INTENT_PARSE_FAIL",
                f"JSON decode error: {exc} | Raw: {cleaned[:120]}",
                "I couldn't parse the routing decision; falling back to conversation.",
                level=logging.WARNING
            )
            return IntentResult(tool_name=None)

        tool_name = payload.get("tool")
        params = payload.get("params", {})

        # Validate: null / "null" / unknown name all map to conversational fallback
        if not tool_name or tool_name == "null" or tool_name not in known_names:
            log_action(
                "INTENT_NO_MATCH",
                f"No tool matched for command. LLM returned: tool={tool_name}",
                "No specific tool matched; routing to conversational brain."
            )
            return IntentResult(tool_name=None)

        # Ensure params is always a dict (guard against unexpected model output)
        if not isinstance(params, dict):
            params = {}

        log_action(
            "INTENT_MATCHED",
            f"Tool: {tool_name} | Params: {params}",
            f"I've decided to use the '{tool_name.replace('_', ' ')}' capability."
        )
        return IntentResult(tool_name=tool_name, params=params)
