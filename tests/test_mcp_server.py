"""Tests for MCP server functionality."""

import pytest

from src.astrology_mcp_server.main import (
    CALCULATE_ASPECTS_TOOL,
    CALCULATE_PLANET_ASPECT_TOOL,
    CALCULATE_TRANSITS_TOOL,
    GET_CURRENT_TIME_TOOL,
    GET_HOUSES_TOOL,
    GET_PLANET_POSITIONS_TOOL,
)


def test_all_tools_are_defined():
    """Verify all expected tools are defined and have proper schemas."""
    tools = [
        CALCULATE_ASPECTS_TOOL,
        CALCULATE_PLANET_ASPECT_TOOL,
        CALCULATE_TRANSITS_TOOL,
        GET_CURRENT_TIME_TOOL,
        GET_HOUSES_TOOL,
        GET_PLANET_POSITIONS_TOOL,
    ]
    
    for tool in tools:
        assert tool is not None
        # Verify inputSchema has required type field
        assert "type" in tool.inputSchema, f"Tool {tool.name} missing 'type' in inputSchema"
        assert tool.inputSchema["type"] == "object", f"Tool {tool.name} type must be 'object'"


def test_get_planet_positions_tool_input_schema():
    """Verify GET_PLANET_POSITIONS_TOOL has proper input schema."""
    assert GET_PLANET_POSITIONS_TOOL.name == "get_planet_positions"
    assert GET_PLANET_POSITIONS_TOOL.inputSchema["type"] == "object"
    assert "properties" in GET_PLANET_POSITIONS_TOOL.inputSchema


def test_calculate_planet_aspect_tool_input_schema():
    """Verify CALCULATE_PLANET_ASPECT_TOOL has proper input schema."""
    assert CALCULATE_PLANET_ASPECT_TOOL.name == "calculate_planet_aspect"
    assert CALCULATE_PLANET_ASPECT_TOOL.inputSchema["type"] == "object"


def test_calculate_aspects_tool_input_schema():
    """Verify CALCULATE_ASPECTS_TOOL has proper input schema."""
    assert CALCULATE_ASPECTS_TOOL.name == "calculate_aspects"
    assert CALCULATE_ASPECTS_TOOL.inputSchema["type"] == "object"


def test_calculate_transits_tool_input_schema():
    """Verify CALCULATE_TRANSITS_TOOL has proper input schema."""
    assert CALCULATE_TRANSITS_TOOL.name == "calculate_transits"
    assert CALCULATE_TRANSITS_TOOL.inputSchema["type"] == "object"


def test_get_houses_tool_input_schema():
    """Verify GET_HOUSES_TOOL has proper input schema."""
    assert GET_HOUSES_TOOL.name == "get_houses"
    assert GET_HOUSES_TOOL.inputSchema["type"] == "object"


def test_get_current_time_tool_input_schema():
    """Verify GET_CURRENT_TIME_TOOL has proper input schema."""
    assert GET_CURRENT_TIME_TOOL.name == "get_current_time"
    # Empty properties object is valid
    assert GET_CURRENT_TIME_TOOL.inputSchema["type"] == "object"
    assert "properties" in GET_CURRENT_TIME_TOOL.inputSchema
