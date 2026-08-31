"""Astrology MCP Server - Main module.

This module initializes and runs the Astrology MCP Server with all tools
and handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

# Configure logging - write to file instead of stderr to avoid interfering with MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('astrology_mcp_server.log'),
    ],
)
logger = logging.getLogger(__name__)

# Import server framework
try:
    from mcp.server.stdio import stdio_server
    from mcp.server.lowlevel import Server
    from mcp.types import TextContent
except ImportError:
    raise ImportError(
        "MCP server not found. Install with: pip install mcp"
    )

# Import serializers functions for testing
from .serializers import _serialize_chart, _deserialize_zonal

# Import handlers
from .handlers import (
    handle_calculate_natal_chart,
    handle_get_result,
    handle_get_planet_positions,
    handle_calculate_aspects,
    handle_calculate_transits,
    handle_scan_transits,
    handle_calculate_planet_aspect,
    handle_lunation_scan,
    handle_get_houses,
)

# Import cache for cleanup on startup
from . import cache as cache_module

# Import tools
from .tools import (
    CALCULATE_NATAL_CHART_TOOL,
    GET_RESULT_TOOL,
    GET_PLANET_POSITIONS_TOOL,
    CALCULATE_ASPECTS_TOOL,
    CALCULATE_TRANSITS_TOOL,
    GET_HOUSES_TOOL,
    GET_CURRENT_TIME_TOOL,
    CALCULATE_PLANET_ASPECT_TOOL,
    LUNATION_SCAN_TOOL,
    SCAN_TRANSITS_TOOL,
)

# Tool name to handler mapping
TOOL_HANDLERS: dict[str, Any] = {
    "calculate_natal_chart": handle_calculate_natal_chart,
    "get_result": handle_get_result,
    "get_planet_positions": handle_get_planet_positions,
    "calculate_aspects": handle_calculate_aspects,
    "calculate_transits": handle_calculate_transits,
    "get_houses": handle_get_houses,
    "lunation_scan": handle_lunation_scan,
    "calculate_planet_aspect": handle_calculate_planet_aspect,
    "scan_transits": handle_scan_transits,
}

# List of all tools
ALL_TOOLS = [
    CALCULATE_NATAL_CHART_TOOL,
    GET_RESULT_TOOL,
    GET_PLANET_POSITIONS_TOOL,
    CALCULATE_ASPECTS_TOOL,
    CALCULATE_TRANSITS_TOOL,
    GET_HOUSES_TOOL,
    GET_CURRENT_TIME_TOOL,
    CALCULATE_PLANET_ASPECT_TOOL,
    LUNATION_SCAN_TOOL,
    SCAN_TRANSITS_TOOL,
]


async def _handle_get_current_time(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_current_time tool call."""
    now = datetime.now(timezone.utc)

    result = {
        "utc_datetime": now.isoformat(),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
    }

    # Include cache statistics for debugging
    cache_stats = cache_module._get_cache_stats()
    result["cache_stats"] = {
        "hits": cache_stats["hits"],
        "misses": cache_stats["misses"],
        "expired": cache_stats["expired"],
        "total_cached": cache_stats["total_cached"],
    }

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2),
    )]

async def _handle_tool_call(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to appropriate handlers.
    
    Args:
        name: Name of the tool being called
        arguments: Dictionary of arguments for the tool
    
    Returns:
        List of TextContent responses
    
    Raises:
        ValueError: If unknown tool name
    """
    if name == "get_current_time":
        return await _handle_get_current_time(arguments)
    
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    
    return await handler(arguments)


def main():
    """Run the Astrology MCP Server."""
    async def run_server():
        """Run the MCP server asynchronously."""
        logger.info("Starting Astrology MCP Server...")

        # Clean up expired cache entries on startup
        cleaned = cache_module._cleanup_expired_results()
        if cleaned > 0:
            logger.info(f"Cache cleanup on startup: removed {cleaned} expired entries")
        else:
            logger.debug("Cache check: no expired entries found")

        # Create server instance with tools
        server = Server(name="astrology")
        
        @server.list_tools()
        async def list_tools() -> list[Any]:
            """List all available tools."""
            return ALL_TOOLS
        
        @server.call_tool()
        async def call_tool(
            name: str,
            arguments: dict[str, Any],
        ) -> list[TextContent]:
            """Handle tool calls."""
            return await _handle_tool_call(name, arguments)
        
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server ready, waiting for connections...")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
