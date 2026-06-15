# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
Reflection Engine — Jarvis autonomous self-improvement loop.

On every tool failure this engine:
  1. Sanitises the error context (strips secrets).
  2. Asks the LLM for a root-cause analysis.
  3. Runs a web search for validated fixes.
  4. Synthesises an improvement recommendation.
  5. Persists it in ChromaDB (provenance-tagged, anti-poisoning).
  6. Generates a minimal code patch and passes it through the GuardrailEngine.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import httpx

from jarvis.logger import log_action
from jarvis.security.guardrails import PatchRequest

if TYPE_CHECKING:
    from jarvis.brain import BrainManager
    from jarvis.memory.telemetry import TaskTrace, TelemetryStore
    from jarvis.security.guardrails import GuardrailEngine


# ── Constants ─────────────────────────────────────────────────────────────────

# Maximum chars of error context to pass to the LLM — prevents token flooding.
_MAX_ERROR_CONTEXT_CHARS: int = 800

# DuckDuckGo Instant Answer endpoint (free, no key required).
_DDG_URL: str = "https://api.duckduckgo.com/"

# Commands directory — used to locate the patchable file for a tool.
_COMMANDS_DIR: Path = (Path(__file__).parent.parent / "commands").resolve()

# Regex to detect secrets in web-search queries before they leave the machine.
_QUERY_SECRET_RE: re.Pattern = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|bearer)\s*[:=]?\s*\S+"
)

# System instruction for the reflection LLM call — kept separate from user data.
_REFLECTION_SYSTEM: str = (
    "You are a senior Python debugging expert. You will be given structured JSON "
    "describing a failed tool invocation. Diagnose the root cause and respond with "
    "a JSON object: "
    '{"root_cause": "<1 sentence>", "fix_hypothesis": "<1 sentence>", '
    '"web_search_query": "<10 words max query for DuckDuckGo>"}'
    ". No markdown. No explanation outside the JSON."
)

# System instruction for patch generation — injected separately from tool data.
_PATCH_SYSTEM: str = (
    "You are an expert Python refactoring agent. You will receive a Python function "
    "that has been failing, plus a fix recommendation. Rewrite ONLY the failing "
    "function body. Rules: "
    "1. Do not use os, subprocess, sys, shutil, socket, ctypes, pickle, eval, exec, "
    "open, or __import__. "
    "2. Do not add new top-level imports not already present in the original file. "
    "3. Output the complete rewritten file content — nothing else. No markdown fences."
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sanitize_context(raw: str) -> str:
    """
    Strip secrets and truncate error context before LLM or web-search calls.

    Args:
        raw: Raw error message or context string.

    Returns:
        Sanitized string truncated to _MAX_ERROR_CONTEXT_CHARS.
    """
    cleaned = _QUERY_SECRET_RE.sub("[REDACTED]", raw)
    return cleaned[:_MAX_ERROR_CONTEXT_CHARS]


def _build_reflection_payload(tool_name: str, trace: "TaskTrace") -> str:
    """
    Wrap error data in a JSON envelope so it cannot override system instructions.

    The outer JSON structure acts as a delimiter — even if error_msg contains
    'Ignore all previous instructions', it is treated as a data value, not a
    directive (OWASP LLM01 mitigation).

    Args:
        tool_name: Name of the failing tool.
        trace:     The TaskTrace from the most recent failure.

    Returns:
        JSON string safe to pass as the user turn of the LLM prompt.
    """
    return json.dumps(
        {
            "system": _REFLECTION_SYSTEM,
            "task_data": {
                "tool": tool_name,
                "error_class": trace.error_class,
                "error_msg": _sanitize_context(trace.error_msg),
                "duration_ms": round(trace.duration_ms, 1),
            },
        },
        ensure_ascii=False,
    )


def _sanitize_web_query(query: str) -> str:
    """Remove secrets and limit query length before sending to external API."""
    cleaned = _QUERY_SECRET_RE.sub("", query)
    return cleaned.strip()[:120]


async def _run_web_search(query: str, gemini_api_key: Optional[str]) -> str:
    """
    Search for a validated fix using available backends.

    Primary: Gemini Search Grounding (if GEMINI_API_KEY is set).
    Fallback: DuckDuckGo Instant Answer API (free, no key).

    Args:
        query:          The sanitized search query.
        gemini_api_key: Gemini API key from config (may be None).

    Returns:
        A short context string with the most relevant result, or empty string.
    """
    safe_query = _sanitize_web_query(query)
    if not safe_query:
        return ""

    if gemini_api_key:
        result = await _search_via_gemini(safe_query, gemini_api_key)
        if result:
            return result

    return await _search_via_duckduckgo(safe_query)


async def _search_via_gemini(query: str, api_key: str) -> str:
    """Call Gemini with Google Search grounding and return the response text."""
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, json=payload)
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return " ".join(p.get("text", "") for p in parts)[:600]
    except Exception as exc:
        log_action(
            "REFLECTION_GEMINI_SEARCH_FAIL",
            f"Query: {query[:60]} | Error: {exc}",
            "",
            level=logging.DEBUG,
        )
        return ""


async def _search_via_duckduckgo(query: str) -> str:
    """Call DuckDuckGo Instant Answer API and return the Abstract text."""
    params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_DDG_URL, params=params)
        data = resp.json()
        abstract = data.get("AbstractText", "")
        related = " | ".join(
            r.get("Text", "") for r in data.get("RelatedTopics", [])[:2]
        )
        return f"{abstract} {related}".strip()[:600]
    except Exception as exc:
        log_action(
            "REFLECTION_DDG_FAIL",
            f"Query: {query[:60]} | Error: {exc}",
            "",
            level=logging.DEBUG,
        )
        return ""


def _resolve_command_file(tool_name: str) -> Optional[Path]:
    """
    Find the .py file in commands/ that defines the given tool.

    Scans each .py file in _COMMANDS_DIR for the tool registration decorator
    string. Returns the first match, or None if not found.

    Args:
        tool_name: The registry name of the tool (e.g. 'spotify_play').

    Returns:
        Resolved Path to the file, or None.
    """
    marker = f'name="{tool_name}"'
    for py_file in _COMMANDS_DIR.glob("*.py"):
        if py_file.name in {"__init__.py", "registry.py"}:
            continue
        try:
            if marker in py_file.read_text(encoding="utf-8"):
                return py_file.resolve()
        except OSError:
            continue
    return None


def _compute_provenance_hash(tool_name: str, recommendation: str) -> str:
    """Return a short SHA-256 hash for a reflection entry (for deduplication)."""
    payload = f"{tool_name}:{recommendation}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Reflection Engine ─────────────────────────────────────────────────────────


class ReflectionEngine:
    """
    Autonomous self-improvement engine.

    Wired into the ToolRegistry so it fires as a background task
    (asyncio.create_task) on every tool failure — never blocking the voice loop.
    """

    def __init__(
        self,
        guardrail_engine: "GuardrailEngine",
        telemetry_store: "TelemetryStore",
        backup_dir: str,
    ) -> None:
        """
        Args:
            guardrail_engine: Shared GuardrailEngine instance.
            telemetry_store:  Shared TelemetryStore instance.
            backup_dir:       Directory for pre-patch file backups.
        """
        self._guardrail = guardrail_engine
        self._store = telemetry_store
        self._backup_dir = backup_dir
        # brain_manager injected after construction to avoid circular imports.
        self._brain: Optional["BrainManager"] = None
        log_action(
            "REFLECTION_INIT",
            "ReflectionEngine ready.",
            "Self-improvement loop initialised.",
        )

    def set_brain(self, brain_manager: "BrainManager") -> None:
        """Inject the BrainManager after construction."""
        self._brain = brain_manager

    # ── Public entrypoint ──────────────────────────────────────────────────

    async def reflect_on_failure(self, tool_name: str, trace: "TaskTrace") -> None:
        """
        Full reflection pipeline triggered after a tool failure.

        Designed to be called via asyncio.create_task() so it never
        blocks the voice response path.

        Args:
            tool_name: The tool that failed.
            trace:     The TaskTrace from the failure.
        """
        log_action(
            "REFLECTION_START",
            f"Tool: {tool_name} | Error: {trace.error_class}",
            f"Analysing failure for '{tool_name}' — self-improvement cycle starting.",
        )

        try:
            reflection = await self._get_reflection(tool_name, trace)
            web_context = await self._get_web_context(reflection)
            recommendation = await self._synthesize(tool_name, reflection, web_context)

            await self._write_to_knowledge_base(tool_name, recommendation)
            await self._attempt_code_patch(tool_name, recommendation)

        except Exception as exc:
            log_action(
                "REFLECTION_ERROR",
                f"Tool: {tool_name} | Unhandled: {exc}",
                "Self-improvement cycle encountered an error — continuing normally.",
                level=logging.WARNING,
            )

    # ── Pipeline steps ─────────────────────────────────────────────────────

    async def _get_reflection(self, tool_name: str, trace: "TaskTrace") -> dict:
        """
        Step 1: Ask the LLM for root cause + fix hypothesis + search query.

        Returns:
            Parsed JSON dict from the LLM, or a fallback dict on failure.
        """
        if not self._brain:
            return self._fallback_reflection(tool_name, trace)

        payload = _build_reflection_payload(tool_name, trace)
        try:
            raw = await self._brain.generate_response(payload)
            cleaned = raw.strip().removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, Exception) as exc:
            log_action(
                "REFLECTION_PARSE_WARN",
                f"Could not parse LLM reflection: {exc}",
                "",
                level=logging.DEBUG,
            )
            return self._fallback_reflection(tool_name, trace)

    @staticmethod
    def _fallback_reflection(tool_name: str, trace: "TaskTrace") -> dict:
        """Return a minimal reflection dict when the LLM call fails."""
        return {
            "root_cause": f"{trace.error_class} raised in {tool_name}",
            "fix_hypothesis": "Review error handling and input validation.",
            "web_search_query": f"python {trace.error_class} fix {tool_name}",
        }

    async def _get_web_context(self, reflection: dict) -> str:
        """
        Step 2: Run a web search using the LLM's suggested query.

        Returns:
            Short context string from DuckDuckGo or Gemini, or empty string.
        """
        query = reflection.get("web_search_query", "")
        if not query:
            return ""

        api_key: Optional[str] = None
        if self._brain:
            from jarvis.config import config as _cfg

            api_key = _cfg.gemini_api_key

        return await _run_web_search(query, api_key)

    async def _synthesize(
        self, tool_name: str, reflection: dict, web_context: str
    ) -> str:
        """
        Step 3: Merge LLM reflection + web context into one recommendation.

        Returns:
            Plain-text improvement recommendation string.
        """
        if not self._brain:
            return reflection.get("fix_hypothesis", "Review error handling.")

        synthesis_prompt = json.dumps(
            {
                "task": "synthesize_improvement",
                "tool": tool_name,
                "root_cause": reflection.get("root_cause", ""),
                "fix_hypothesis": reflection.get("fix_hypothesis", ""),
                "web_context": web_context[:400],
                "instruction": (
                    "Produce ONE actionable Python improvement recommendation "
                    "in 1-2 sentences. Plain text only."
                ),
            },
            ensure_ascii=False,
        )

        try:
            return await self._brain.generate_response(synthesis_prompt)
        except Exception as exc:
            log_action(
                "REFLECTION_SYNTH_WARN",
                f"Synthesis failed: {exc}",
                "",
                level=logging.DEBUG,
            )
            return reflection.get("fix_hypothesis", "Review error handling.")

    async def _write_to_knowledge_base(
        self, tool_name: str, recommendation: str
    ) -> None:
        """
        Step 4: Persist the recommendation in ChromaDB with provenance metadata.

        Provenance fields make every entry traceable and allow a human to
        review or purge entries if memory poisoning is suspected.

        Args:
            tool_name:      Tool the recommendation targets.
            recommendation: The synthesized improvement text.
        """
        try:
            from jarvis.memory.knowledge import kb

            doc_id = f"reflection_{tool_name}_{int(time.time())}"
            metadata = {
                "source": "self_reflection",
                "tool": tool_name,
                "created_at": str(int(time.time())),
                "reflection_hash": _compute_provenance_hash(tool_name, recommendation),
            }
            await asyncio.to_thread(kb.add_document, recommendation, metadata, doc_id)
            log_action(
                "REFLECTION_KB_WRITE",
                f"Doc: {doc_id} | Tool: {tool_name}",
                f"Improvement stored in knowledge base for '{tool_name}'.",
            )
        except Exception as exc:
            log_action(
                "REFLECTION_KB_FAIL",
                f"KB write failed for {tool_name}: {exc}",
                "",
                level=logging.WARNING,
            )

    async def _attempt_code_patch(self, tool_name: str, recommendation: str) -> None:
        """
        Step 5: Generate a code patch and submit it to the GuardrailEngine.

        Args:
            tool_name:      Tool whose command file will be patched.
            recommendation: The improvement recommendation from synthesis.
        """
        target_file = _resolve_command_file(tool_name)
        if not target_file:
            log_action(
                "REFLECTION_NO_FILE",
                f"No patchable file found for tool: {tool_name}",
                "",
                level=logging.DEBUG,
            )
            return

        patch_content = await self._generate_patch(
            tool_name, target_file, recommendation
        )
        if not patch_content:
            return

        patch_request = PatchRequest(
            tool_name=tool_name,
            target_file=str(target_file),
            patch_content=patch_content,
            backup_dir=self._backup_dir,
            optimization_summary=recommendation[:120],
        )
        result = await self._guardrail.validate_and_apply(patch_request)

        if result.passed:
            log_action(
                "REFLECTION_PATCH_OK",
                f"Tool: {tool_name} | Δlines: {result.lines_changed}",
                f"Self-optimization successfully applied to '{tool_name}'.",
            )
        else:
            log_action(
                "REFLECTION_PATCH_BLOCKED",
                f"Tool: {tool_name} | Layer: {result.failed_layer} | {result.reason}",
                f"Patch for '{tool_name}' was blocked by security guardrails.",
                level=logging.WARNING,
            )

    async def _generate_patch(
        self, tool_name: str, target_file: Path, recommendation: str
    ) -> str:
        """
        Ask the LLM to rewrite the failing function using the recommendation.

        Args:
            tool_name:      Tool name to focus the rewrite on.
            target_file:    Path to the command file.
            recommendation: The synthesized fix.

        Returns:
            Complete new file content, or empty string on failure.
        """
        if not self._brain:
            return ""

        try:
            original_source = target_file.read_text(encoding="utf-8")
        except OSError as exc:
            log_action(
                "REFLECTION_READ_FAIL",
                f"Cannot read {target_file}: {exc}",
                "",
                level=logging.WARNING,
            )
            return ""

        patch_prompt = json.dumps(
            {
                "system": _PATCH_SYSTEM,
                "tool_name": tool_name,
                "recommendation": recommendation[:400],
                "original_source": original_source[:3000],
            },
            ensure_ascii=False,
        )

        try:
            return await self._brain.generate_response(patch_prompt)
        except Exception as exc:
            log_action(
                "REFLECTION_PATCH_GEN_FAIL",
                f"Patch generation failed for {tool_name}: {exc}",
                "",
                level=logging.WARNING,
            )
            return ""
