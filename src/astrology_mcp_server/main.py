"""MCP Server for Astrology calculations.

This module provides the entry point for the Astrology MCP server.
It imports from refactored modules to provide all astrology tools
for use with local LLMs via tool calling interface.
"""

from __future__ import annotations

# Re-export all components from refactored modules
from astrology_mcp_server import __init__ as main_mod

# This is a simple wrapper that imports from our refactored modules
if __name__ == "__main__":
    main_mod.main()
