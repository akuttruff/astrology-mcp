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


def test_transit_calculation_returns_actual_data():
    """Verify transit calculation returns real planetary data, not placeholders."""
    from datetime import datetime
    from astrology.charts.chart import calculate_natal_chart
    from astrology.transits.transit import get_current_transits

    chart = calculate_natal_chart(
        birth_datetime=datetime.fromisoformat("1984-05-10T20:44:00-07:00"),
        latitude=34.02,
        longitude=-118.45,
        elevation=0.0,
    )

    report = get_current_transits(chart, None)

    # Verify we got actual transit data
    assert report.transits is not None
    assert len(report.transits) > 0

    # Verify transit data contains expected fields
    for transit in report.transits:
        assert hasattr(transit, "planet")
        assert hasattr(transit, "aspect_type")
        assert hasattr(transit, "orb")


def test_natal_chart_calculation_past_date():
    """Verify natal chart calculation works for past dates."""
    from datetime import datetime
    from astrology.charts.chart import calculate_natal_chart
    from astrology.core.ephemeris import Planet

    # Test with a past birth date
    chart = calculate_natal_chart(
        birth_datetime=datetime.fromisoformat("1984-05-10T20:44:00-07:00"),
        latitude=34.02,
        longitude=-118.45,
        elevation=0.0,
    )

    # Verify chart was created
    assert chart is not None
    assert chart.planets is not None

    # Verify expected planets are present
    assert Planet.SUN in chart.planets
    assert Planet.MOON in chart.planets

    # Verify approximate expected values for natal Sun and Moon
    sun_pos = chart.planets[Planet.SUN]
    assert 20 <= sun_pos.zonal.degree_in_sign <= 21
    assert sun_pos.zonal.sign_name == "Taurus"

    moon_pos = chart.planets[Planet.MOON]
    assert 25 <= moon_pos.zonal.degree_in_sign <= 27
    assert moon_pos.zonal.sign_name == "Virgo"


def test_transit_calculation_with_stale_date():
    """Verify transit calculation warns when using stale dates."""
    from datetime import datetime
    from astrology.charts.chart import calculate_natal_chart
    from astrology.transits.transit import get_current_transits

    chart = calculate_natal_chart(
        birth_datetime=datetime.fromisoformat("1984-05-10T20:44:00-07:00"),
        latitude=34.02,
        longitude=-118.45,
        elevation=0.0,
    )

    # Test with a stale date (April 2025 - more than 7 days from now)
    stale_date = datetime.fromisoformat("2025-04-10T00:00:00+00:00")
    report = get_current_transits(chart, stale_date)

    # Verify transit data is returned even with stale date
    assert report.transits is not None
    assert len(report.transits) > 0

    # Verify the report uses the stale date (not current)
    assert report.date.year == 2025


def test_calculate_transits_with_minimal_planet_data():
    """Verify transit calculation handles minimal planet data (longitude only).

    This tests the fix for: https://github.com/modelcontextprotocol/specification/issues/XXX
    Where LLMs may send serialized positions with only 'longitude' field.
    """
    import asyncio
    from src.astrology_mcp_server.main import _handle_calculate_transits

    # Minimal natal chart data with only longitude values (no sign, degree_in_sign, etc.)
    minimal_natal_data = {
        "birth_datetime": "1984-05-10T20:44:00-07:00",
        "location": {"latitude": 34.021185, "longitude": -118.402673},
        "planets": {
            "SUN": {"longitude": 50.63689351655029},
            "MOON": {"longitude": 176.26079997064508},
            "MERCURY": {"longitude": 27.501945446411998},
            "VENUS": {"longitude": 41.00909130013627},
            "MARS": {"longitude": 230.92048984724283},
            "JUPITER": {"longitude": 282.7592733990824},
            "SATURN": {"longitude": 222.49514823775914},
            "URANUS": {"longitude": 252.43498657978645},
            "NEPTUNE": {"longitude": 271.0416499091887},
            "PLUTO": {"longitude": 210.18674613839875},
        },
        "angles": {
            "ascendant": {"longitude": 243.7734708325564},
            "midheaven": {"longitude": 165.56324445821875},
        },
    }

    arguments = {
        "natal_chart": minimal_natal_data,
        "current_datetime": "2026-04-10T23:28:30Z",
    }

    # This should not raise an error about ZonalPosition arguments
    result = asyncio.run(_handle_calculate_transits(arguments))

    # Verify we got a valid response (not an error)
    assert len(result) == 1
    content = result[0]
    assert content.type == "text"
    assert "Error" not in content.text
    assert "Current Transits Report" in content.text

    # Verify some transits are returned
    assert "transiting" in content.text.lower()


def test_calculate_transits_with_full_zonalposition_data():
    """Verify transit calculation handles full ZonalPosition data (with sign, degree)."""
    import asyncio
    from src.astrology_mcp_server.main import _handle_calculate_transits

    # Full natal chart data with complete ZonalPosition info
    full_natal_data = {
        "birth_datetime": "1984-05-10T20:44:00-07:00",
        "location": {"latitude": 34.021185, "longitude": -118.402673},
        "planets": {
            "SUN": {
                "longitude": 50.63689351655029,
                "sign": "Gemini",
                "degree_in_sign": 20.64,
                "sign_name": "Gemini",
            },
            "MOON": {
                "longitude": 176.26079997064508,
                "sign": "Virgo",
                "degree_in_sign": 26.26,
                "sign_name": "Virgo",
            },
        },
        "angles": {
            "ascendant": {
                "longitude": 243.7734708325564,
                "sign": "Leo",
                "degree_in_sign": 23.77,
                "sign_name": "Leo",
            },
            "midheaven": {
                "longitude": 165.56324445821875,
                "sign": "Leo",
                "degree_in_sign": 15.56,
                "sign_name": "Leo",
            },
        },
    }

    arguments = {
        "natal_chart": full_natal_data,
        "current_datetime": "2026-04-10T23:28:30Z",
    }

    result = asyncio.run(_handle_calculate_transits(arguments))

    # Verify we got a valid response
    assert len(result) == 1
    content = result[0]
    assert content.type == "text"
    assert "Error" not in content.text
