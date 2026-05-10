# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Tool registration system for Jarvis."""
import functools
import inspect
import logging
from typing import Any, Callable, Dict, Optional, List

from jarvis.logger import log_action


class ToolRegistry:
    """Registry to manage and dispatch system tools."""

    _tools: Dict[str, Dict[str, Any]] = {}

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
                "params": func.__annotations__
            }
            log_action(
                "TOOL_REG",
                f"Tool registered: {name}",
                f"Initialized {name} capability.",
                level=logging.DEBUG
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
        Invoke a tool by name (supports both sync and async tools).

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
            f"I'm running the {name.replace('_', ' ')} command."
        )

        if inspect.iscoroutinefunction(tool):
            return await tool(*args, **kwargs)

        return tool(*args, **kwargs)


# Global registry instance
registry = ToolRegistry()
