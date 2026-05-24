"""
Tests for jarvis/commands/registry.py — ToolRegistry.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from jarvis.commands.registry import ToolRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the ToolRegistry between tests to avoid cross-test contamination."""
    original = dict(ToolRegistry._tools)
    yield
    ToolRegistry._tools.clear()
    ToolRegistry._tools.update(original)


class TestToolRegistryRegister:
    """Tests for the @register decorator."""

    def test_register_adds_tool(self):
        """Registering a function should add it to _tools."""
        @ToolRegistry.register(name="test_tool", description="A test tool.")
        def my_tool():
            return "result"

        assert "test_tool" in ToolRegistry._tools

    def test_register_stores_description(self):
        """Registered tool should store the correct description."""
        @ToolRegistry.register(name="desc_tool", description="My description.")
        def my_tool():
            pass

        assert ToolRegistry._tools["desc_tool"]["description"] == "My description."

    def test_register_stores_function(self):
        """Registered tool should store the original callable."""
        def raw_fn():
            return "raw"

        ToolRegistry.register(name="fn_tool", description="fn")(raw_fn)
        stored = ToolRegistry._tools["fn_tool"]["func"]
        assert stored is raw_fn

    def test_register_preserves_function_behavior(self):
        """The wrapped function should still return the original value."""
        @ToolRegistry.register(name="behavior_tool", description="test")
        def my_tool(x):
            return x * 2

        assert my_tool(5) == 10


class TestToolRegistryGetTool:
    """Tests for get_tool()."""

    def test_get_existing_tool_returns_callable(self):
        """get_tool() should return the registered function."""
        @ToolRegistry.register(name="gettable_tool", description="test")
        def my_fn():
            return True

        result = ToolRegistry.get_tool("gettable_tool")
        assert callable(result)

    def test_get_nonexistent_tool_returns_none(self):
        """get_tool() should return None for an unknown tool name."""
        result = ToolRegistry.get_tool("does_not_exist_xyz")
        assert result is None


class TestToolRegistryListTools:
    """Tests for list_tools()."""

    def test_list_tools_returns_list(self):
        """list_tools() should always return a list."""
        result = ToolRegistry.list_tools()
        assert isinstance(result, list)

    def test_list_tools_contains_registered_tool(self):
        """list_tools() should include newly registered tools."""
        @ToolRegistry.register(name="listed_tool", description="I am listed.")
        def my_fn():
            pass

        tools = ToolRegistry.list_tools()
        names = [t["name"] for t in tools]
        assert "listed_tool" in names

    def test_list_tools_entry_has_name_and_description(self):
        """Each entry in list_tools() should have 'name' and 'description' keys."""
        @ToolRegistry.register(name="struct_tool", description="Has structure.")
        def my_fn():
            pass

        tools = ToolRegistry.list_tools()
        tool = next(t for t in tools if t["name"] == "struct_tool")
        assert "name" in tool
        assert "description" in tool


class TestToolRegistryInvoke:
    """Tests for invoke()."""

    @pytest.mark.asyncio
    async def test_invoke_sync_tool(self):
        """invoke() should call a synchronous tool and return its result."""
        @ToolRegistry.register(name="sync_invoke_tool", description="sync")
        def my_sync():
            return "sync result"

        result = await ToolRegistry.invoke("sync_invoke_tool")
        assert result == "sync result"

    @pytest.mark.asyncio
    async def test_invoke_async_tool(self):
        """invoke() should await an asynchronous tool."""
        @ToolRegistry.register(name="async_invoke_tool", description="async")
        async def my_async():
            return "async result"

        result = await ToolRegistry.invoke("async_invoke_tool")
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_invoke_passes_kwargs(self):
        """invoke() should forward keyword arguments to the tool."""
        @ToolRegistry.register(name="kwarg_tool", description="kwargs")
        def my_tool(city: str):
            return f"Weather for {city}"

        result = await ToolRegistry.invoke("kwarg_tool", city="London")
        assert result == "Weather for London"

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool_raises_value_error(self):
        """invoke() should raise ValueError for unknown tool names."""
        with pytest.raises(ValueError, match="not found"):
            await ToolRegistry.invoke("unknown_tool_xyz")
