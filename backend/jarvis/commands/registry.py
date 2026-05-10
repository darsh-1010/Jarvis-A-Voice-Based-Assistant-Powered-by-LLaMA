# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Tool registration system for Jarvis."""
import functools
import logging
from typing import Any, Callable, Dict, Optional, List
from jarvis.logger import log_action

class ToolRegistry:
    """Registry to manage and dispatch system tools."""
    
    _tools: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, description: str):
        """Decorator to register a function as a tool."""
        def decorator(func: Callable):
            cls._tools[name] = {
                "func": func,
                "description": description,
                "params": func.__annotations__
            }
            log_action("TOOL_REG", f"Tool registered: {name}", f"Initialized {name} capability.", level=logging.DEBUG)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        """Get a tool function by name."""
        tool_data = cls._tools.get(name)
        return tool_data["func"] if tool_data else None

    @classmethod
    def list_tools(cls) -> List[Dict[str, str]]:
        """List all registered tools with descriptions."""
        return [
            {"name": name, "description": data["description"]}
            for name, data in cls._tools.items()
        ]

    @classmethod
    async def invoke(cls, name: str, *args, **kwargs) -> Any:
        """Invoke a tool by name (supports both sync and async tools)."""
        tool = cls.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found.")
        
        import inspect
        log_action("TOOL_INVOKE", f"Executing: {name} | Params: {kwargs}", f"I'm running the {name.replace('_', ' ')} command.")
        if inspect.iscoroutinefunction(tool):
            return await tool(*args, **kwargs)
        else:
            return tool(*args, **kwargs)

# Global registry instance
registry = ToolRegistry()
