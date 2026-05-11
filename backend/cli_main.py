# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Main entry point for Jarvis AI Assistant (V3.0 Async)."""
import asyncio
import datetime
import logging
import os
import sys
from typing import Any

# Path injection must precede jarvis imports; kept at module level intentionally.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis.audio import AudioManager
from jarvis.brain import BrainManager
import jarvis.commands.system        # noqa: F401 — side-effect: registers system tools
import jarvis.commands.media         # noqa: F401 — side-effect: registers media tools
import jarvis.commands.web           # noqa: F401 — side-effect: registers web tools
import jarvis.commands.vision        # noqa: F401 — side-effect: registers vision tools
import jarvis.commands.weather       # noqa: F401 — side-effect: registers weather tools
import jarvis.commands.finance       # noqa: F401 — side-effect: registers finance tools
import jarvis.commands.productivity  # noqa: F401 — side-effect: registers productivity tools
import jarvis.commands.calendar_cmd  # noqa: F401 — side-effect: registers calendar tools
import jarvis.commands.gmail_cmd     # noqa: F401 — side-effect: registers gmail tools
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.intent import IntentRouter
from jarvis.logger import log_action


# ──────────────────────────────────────────────
# Result Enrichment Helpers
# ──────────────────────────────────────────────

# Tools whose raw output should be summarised by the LLM before speaking.
_LLM_ENRICHABLE_TOOLS = {"fetch_latest_news", "test_internet_speed"}

# Tools that already return a spoken-ready string — passed through directly.
# Adding a tool here avoids a redundant LLM round-trip for self-describing results.
_SPOKEN_RESULT_TOOLS = {
    "get_weather", "get_forecast",
    "get_crypto_price", "get_stock_price", "get_stock_history",
    "get_system_health", "list_processes", "kill_process",
    "spotify_play", "spotify_pause", "spotify_next", "spotify_previous",
    "start_pomodoro", "translate_text", "morning_briefing",
    "read_inbox", "send_email",
    "list_calendar_events", "create_calendar_event",
}

_ENRICHABLE_TOOLS = _LLM_ENRICHABLE_TOOLS | _SPOKEN_RESULT_TOOLS


async def _enrich_news(headlines: list, brain: BrainManager) -> str:
    """
    Summarise raw news headlines into a spoken-friendly briefing via LLM.

    Args:
        headlines: List of news title strings from NewsAPI.
        brain:     Active BrainManager used to call the LLM.

    Returns:
        A concise spoken summary of the headlines.
    """
    if not headlines:
        return "I couldn't find any news headlines right now, sir."

    bullet_list = "\n".join(f"- {h}" for h in headlines)
    prompt = (
        "You are a news briefing assistant. Summarise the following headlines into "
        "a natural, spoken 2-3 sentence briefing. Be concise and use 'sir' at the end.\n\n"
        f"Headlines:\n{bullet_list}"
    )
    return await brain.generate_response(prompt)


async def _enrich_speed(speed_str: str, brain: BrainManager) -> str:
    """
    Convert a raw speed-test result string into a conversational spoken phrase.

    Args:
        speed_str: Raw result like "Download: 42.10 Mbps | Upload: 11.30 Mbps".
        brain:     Active BrainManager used to call the LLM.

    Returns:
        A friendly spoken description of the speed.
    """
    if not speed_str:
        return "I was unable to measure your internet speed, sir."

    prompt = (
        "Convert this internet speed test result into one friendly spoken sentence "
        f"suitable for a voice assistant. End with 'sir'.\nResult: {speed_str}"
    )
    return await brain.generate_response(prompt)


async def _enrich_result(tool_name: str, result: Any, brain: BrainManager) -> str:
    """
    Post-process a tool's raw output into a spoken-friendly response.

    For enrichable tools the LLM generates a natural-language summary.
    For all other tools a simple confirmation is returned.

    Args:
        tool_name: Name of the tool that was invoked.
        result:    Raw return value from the tool function.
        brain:     Active BrainManager for LLM enrichment calls.

    Returns:
        A string ready to be passed directly to AudioManager.speak().
    """
    if tool_name not in _ENRICHABLE_TOOLS:
        return "Done, sir."

    # Pass-through: tool already returned a spoken-ready string
    if tool_name in _SPOKEN_RESULT_TOOLS:
        return result if isinstance(result, str) else "Done, sir."

    if tool_name == "fetch_latest_news":
        return await _enrich_news(result if isinstance(result, list) else [], brain)

    if tool_name == "test_internet_speed":
        return await _enrich_speed(result if isinstance(result, str) else "", brain)

    return "Done, sir."


# ──────────────────────────────────────────────
# Jarvis Controller
# ──────────────────────────────────────────────

class Jarvis:
    """The Jarvis AI Assistant controller (Async)."""

    def __init__(self):
        """Initialize all managers and attach the intent router."""
        self.audio = AudioManager()
        self.brain = BrainManager()
        self.intent_router = IntentRouter(self.brain)
        self.is_running = True

    async def greet(self) -> None:
        """Greet the user based on the time of day."""
        hour = datetime.datetime.now().hour
        if 0 <= hour < 12:
            greeting = "Good Morning, sir."
        elif 12 <= hour < 18:
            greeting = "Good Afternoon, sir."
        else:
            greeting = "Good Evening, sir."
        await self.audio.speak(greeting)
        await self.audio.speak("I am Jarvis. How can I help you today?")

    async def handle_command(self, command: str) -> bool:
        """
        Process a single voice command using AI intent routing or the brain.

        The pipeline is:
          1. Termination / sleep guard (checked before any LLM call).
          2. IntentRouter classifies the command → tool + params via LLM.
          3. If a tool is matched, invoke it and enrich the output for speech.
          4. Otherwise, fall through to the conversational BrainManager.

        Args:
            command: The user's recognised voice command.

        Returns:
            bool: True to keep running, False to terminate/sleep.
        """
        if not command:
            return True

        log_action(
            "COMMAND_EXEC",
            f"Input: '{command}'",
            f"I'm processing your request: '{command}'"
        )

        try:
            # 1. Termination / Sleep — always checked first, before any LLM cost
            if "terminate" in command:
                await self.audio.speak("Shutting down. Have a great day!")
                self.is_running = False
                return False
            if "sleep" in command:
                await self.audio.speak("Going to sleep. Say my name to wake me up.")
                return False

            # 2. AI intent classification — LLM picks the best tool and extracts params
            tools = registry.list_tools()
            intent = await self.intent_router.classify(command, tools)

            if intent.tool_name:
                # 3. Tool matched — invoke it, then enrich raw output for speech
                raw_result = await registry.invoke(intent.tool_name, **intent.params)
                spoken = await _enrich_result(intent.tool_name, raw_result, self.brain)
                await self.audio.speak(spoken)
            else:
                # 4. No tool matched — route to conversational brain as fallback
                response = await self.brain.generate_response(command)
                await self.audio.speak(response)

        except Exception as exc:
            log_action(
                "COMMAND_FAIL",
                f"Error: {exc}",
                "Something went wrong, sir. I'll analyse the issue.",
                level=logging.ERROR
            )
            await self.audio.speak("Something went wrong, sir. Let me analyse the issue.")
            analysis = await self.brain.analyze_error(command, str(exc))
            await self.audio.speak(analysis)

        return True

    async def run(self) -> None:
        """Main loop: wake-word detection → active listening → command dispatch."""
        log_action(
            "SYSTEM_START",
            "Jarvis V3.0 async loop active.",
            "I'm online and ready to help."
        )
        while self.is_running:
            text = await self.audio.listen("Waiting for wake word...")
            if config.wake_word in text:
                await self.greet()
                while True:
                    cmd = await self.audio.listen("Listening for command...")
                    if not cmd:
                        continue
                    if not await self.handle_command(cmd):
                        break
        log_action(
            "SYSTEM_SHUTDOWN",
            "Assistant loop exited.",
            "I'm going offline. Goodbye!"
        )


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

async def main() -> None:
    """Entry point function."""
    assistant = Jarvis()
    try:
        await assistant.run()
    except KeyboardInterrupt:
        log_action("SYSTEM_EXIT", "Manual interrupt.", "I've been stopped manually.")
    except Exception as exc:
        log_action(
            "SYSTEM_FATAL",
            f"Critical fail: {exc}",
            "A critical error occurred.",
            level=logging.ERROR
        )


if __name__ == "__main__":
    asyncio.run(main())
