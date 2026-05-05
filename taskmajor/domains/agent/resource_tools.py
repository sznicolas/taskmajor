"""Wrapper tools for exposing MCP resources as callable tools."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai import RunContext, Tool
from pydantic_ai.mcp import MCPServer


def create_resource_tools(mcp_server: MCPServer) -> list[Tool]:
    """
    Create Tool wrappers for each resource available on an MCP server.

    This makes MCP resources directly accessible as tools to a Pydantic AI agent.

    Args:
        mcp_server: The MCP server instance to get resources from

    Returns:
        A list of Tool objects, one for each available resource
    """
    tools: list[Tool] = []

    async def create_resource_reader(uri: str) -> Callable[[RunContext], Awaitable[Any]]:
        """Create a tool function for reading a specific resource."""
        async def read_resource_tool(ctx: RunContext) -> str:
            """Dynamically generated tool for reading an MCP resource."""
            try:
                content = await mcp_server.read_resource(uri)
                # Handle different content types
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    return "\n".join(str(item) for item in content)
                else:
                    return str(content)
            except Exception as e:
                return f"Error reading resource {uri}: {str(e)}"

        return read_resource_tool

    # Note: We can't use async in a sync context here, so we'll create a simpler approach
    # where we define the tools synchronously but they can call async functions

    def make_resource_reader(resource_uri: str, resource_name: str, resource_desc: str):
        """Factory to create a resource reading tool."""
        async def read_resource(ctx: RunContext) -> str:
            """Read the resource content."""
            try:
                content = await mcp_server.read_resource(resource_uri)
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    return "\n".join(str(item) for item in content)
                else:
                    return str(content)
            except Exception as e:
                return f"Error reading resource {resource_uri}: {str(e)}"

        return Tool(
            name=f"read_resource_{resource_name}",
            description=f"{resource_desc}\n\nResource URI: {resource_uri}",
            function=read_resource,
        )

    # This will be populated at runtime by scanning available resources
    # For now, we return an empty list - the agent will populate this dynamically
    return tools

def create_generic_resource_tool(mcp_server: MCPServer) -> Tool:
    """
    Create a single generic tool that can read any resource by URI.

    This is a more flexible approach that allows reading any resource dynamically.

    Args:
        mcp_server: The MCP server instance

    Returns:
        A Tool that accepts a resource URI and returns its content
    """
    async def read_any_resource(ctx: RunContext, uri: str) -> str:
        """
        Read any available MCP resource by its URI.

        Args:
            uri: The resource URI (e.g., 'taskmajor://project/{project_name}/tasks')

        Returns:
            The content of the resource in string format
        """
        try:
            # First, list available resources
            available = await mcp_server.list_resources()
            available_uris = [r.uri for r in available]

            if uri not in available_uris:
                return (
                    f"Resource '{uri}' not found. Available resources:\n"
                    + "\n".join(f"  - {r.uri}: {r.name or 'No name'}" for r in available)
                )

            # Read the requested resource
            content = await mcp_server.read_resource(uri)

            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                return "\n".join(str(item) for item in content)
            else:
                return str(content)
        except Exception as e:
            return f"Error reading resource: {str(e)}"

    return Tool(
        name="read_mcp_resource",
        description=(
            "Read any available MCP resource by its URI. "
            "Use this to access data from the MCP server. "
            "Example URIs: 'taskmajor://project/{project_name}/tasks'. "
            "Call this tool first to discover available resources."
        ),
        function=read_any_resource,
    )
