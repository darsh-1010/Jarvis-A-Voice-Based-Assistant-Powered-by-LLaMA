# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Tool registration system for Jarvis with integrated telemetry instrumentation."""

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from jarvis.logger import log_action

if TYPE_CHECKING:
    from jarvis.memory.telemetry import TelemetryStore, TaskTrace
    from jarvis.memory.reflection import ReflectionEngine


class ToolRegistry:
    """Registry to manage and dispatch system tools with execution telemetry."""

    _tools: Dict[str, Dict[str, Any]] = {}

    # Injected after construction to avoid circular imports at module load time.
    _telemetry: Optional["TelemetryStore"] = None
    _reflection: Optional["ReflectionEngine"] = None

    @classmethod
    def set_telemetry(cls, store: "TelemetryStore") -> None:
        """
        Inject the shared TelemetryStore.

        Args:
            store: Initialised TelemetryStore instance.
        """
        cls._telemetry = store

    @classmethod
    def set_reflection_engine(cls, engine: "ReflectionEngine") -> None:
        """
        Inject the shared ReflectionEngine.

        Args:
            engine: Initialised ReflectionEngine instance.
        """
        cls._reflection = engine

    @classmethod
    def register(cls, name: str, description: str):
        """
        Decorator to register a function as a tool.

        Args:
            name: The tool's identifier.
            description: What the tool does.
        """

        def decorator(func: Callable):
            cls._tools[name] = {
                "func": func,
                "description": description,
                "params": func.__annotations__,
            }
            log_action(
                "TOOL_REG",
                f"Tool registered: {name}",
                f"Initialized {name} capability.",
                level=logging.DEBUG,
            )

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        """
        Get a tool function by name.

        Args:
            name: The tool's identifier.

        Returns:
            Optional[Callable]: The function if found, else None.
        """
        tool_data = cls._tools.get(name)
        return tool_data["func"] if tool_data else None

    @classmethod
    def list_tools(cls) -> List[Dict[str, str]]:
        """
        List all registered tools with descriptions.

        Returns:
            List[Dict[str, str]]: List of tool data.
        """
        return [
            {"name": name, "description": data["description"]}
            for name, data in cls._tools.items()
        ]

    @classmethod
    async def invoke(cls, name: str, *args, **kwargs) -> Any:
        """
        Invoke a tool by name with telemetry instrumentation.

        Records execution duration and success/failure to the TelemetryStore.
        On failure, fires a background reflection task (non-blocking).

        Args:
            name: The tool's identifier.
            *args: Positional arguments for the tool.
            **kwargs: Keyword arguments for the tool.

        Returns:
            Any: The result of the tool execution.
        """
        tool = cls.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found.")

        log_action(
            "TOOL_INVOKE",
            f"Executing: {name} | Params: {kwargs}",
            f"I'm running the {name.replace('_', ' ')} command.",
        )

        start_ms = time.monotonic() * 1000

        try:
            if inspect.iscoroutinefunction(tool):
                result = await tool(*args, **kwargs)
            else:
                result = tool(*args, **kwargs)

            duration_ms = time.monotonic() * 1000 - start_ms
            await cls._record_success(name, duration_ms)
            return result

        except Exception as exc:
            duration_ms = time.monotonic() * 1000 - start_ms
            trace = await cls._record_failure(
                name, duration_ms, type(exc).__name__, str(exc)
            )
            cls._fire_reflection(name, trace)
            raise

    @classmethod
    async def _record_success(cls, name: str, duration_ms: float) -> None:
        """Persist a success trace if telemetry is available."""
        if cls._telemetry:
            await cls._telemetry.record_success(name, duration_ms)

    @classmethod
    async def _record_failure(
        cls,
        name: str,
        duration_ms: float,
        error_class: str,
        error_msg: str,
    ) -> Optional["TaskTrace"]:
        """Persist a failure trace and return it for the reflection engine."""
        if not cls._telemetry:
            return None
        return await cls._telemetry.record_failure(
            name, duration_ms, error_class, error_msg
        )

    @classmethod
    def _fire_reflection(cls, name: str, trace: Optional["TaskTrace"]) -> None:
        """
        Schedule a reflection task as fire-and-forget (never blocks).

        The reflection runs in the background event loop — the voice response
        path returns immediately regardless of how long analysis takes.
        """
        if not cls._reflection or not trace:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                cls._reflection.reflect_on_failure(name, trace),
                name=f"reflection_{name}",
            )
        except RuntimeError:
            # No running loop (e.g. during tests) — safe to skip
            pass


# Global registry instance
registry = ToolRegistry()
