"""MCP Server for Astrology calculations.

This module provides the entry point for the Astrology MCP server.
For the actual implementation, see __init__.py which contains the main() function.
"""

from __future__ import annotations

# Re-export main function from __init__.py
from astrology_mcp_server.__init__ import main as main_function

# Make the function available as 'main' for backwards compatibility
main = main_function

__all__ = ["main"]
