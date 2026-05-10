# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Main entry point for Jarvis AI Assistant (V3.0 Async)."""
import asyncio
import datetime
import logging
import os
import sys

# Ensure the 'backend' directory is in the path so we can import 'jarvis'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from jarvis.audio import AudioManager
from jarvis.brain import BrainManager
from jarvis.commands import system, media, web
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action


class Jarvis:
    """The Jarvis AI Assistant controller (Async)."""

    def __init__(self):
        """Initialize all managers."""
        self.audio = AudioManager()
        self.brain = BrainManager()
        self.is_running = True
        self._wake_lock = False

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
        Process a single voice command using registry tools or the AI brain.

        Args:
            command: The user's recognized voice command.

        Returns:
            bool: True if the assistant should keep running, False to terminate/sleep.
        """
        if not command:
            return True

        log_action(
            "COMMAND_EXEC",
            f"Input: '{command}'",
            f"I'm processing your request: '{command}'"
        )

        # Small Change: Command Aliases
        aliases = {
            "ss": "take_screenshot",
            "calc": "open_app calculator",
            "notes": "open_app notepad",
            "speed": "test_internet_speed"
        }

        for alias, target in aliases.items():
            if command.lower() == alias:
                command = target
                log_action(
                    "COMMAND_ALIAS",
                    f"Resolved '{alias}' -> '{target}'",
                    f"I've recognized '{alias}' as a shortcut for '{target}'."
                )

        try:
            # 1. Check for Termination/Sleep
            if "terminate" in command:
                await self.audio.speak("Shutting down. Have a great day!")
                self.is_running = False
                return False
            if "sleep" in command:
                await self.audio.speak("Going to sleep. Say my name to wake me up.")
                return False

            # 2. Try Registry Tools (Hardcoded Intent Matching for now)
            # In Phase 3, the Brain will handle this via Tool-Use/Function-Calling
            tools = registry.list_tools()
            for tool in tools:
                if tool["name"].replace("_", " ") in command:
                    log_action(
                        "COMMAND_TOOL",
                        f"Matched: {tool['name']}",
                        "I've found a built-in tool to handle your request."
                    )
                    # Simple param extraction (very basic for now)
                    if tool["name"] == "open_app":
                        app = command.replace("open app", "").strip()
                        await registry.invoke("open_app", app_name=app)
                        await self.audio.speak(f"Opening {app}, sir.")
                    else:
                        await registry.invoke(tool["name"])
                        await self.audio.speak("Done, sir.")
                    return True

            # 3. Fallback to AI Brain
            response = await self.brain.generate_response(command)
            await self.audio.speak(response)

        except Exception as exc:
            log_action(
                "COMMAND_FAIL",
                f"Error: {exc}",
                "Something went wrong, sir. I'll analyze the issue.",
                level=logging.ERROR
            )
            await self.audio.speak("Something went wrong, sir. Let me analyze the issue.")
            analysis = await self.brain.analyze_error(command, str(exc))
            await self.audio.speak(analysis)

        return True

    async def run(self) -> None:
        """Main loop of the assistant."""
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

