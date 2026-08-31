"""Tool definitions and parameter classes for Astrology MCP Server.

This module contains all the Pydantic parameter models and Tool definitions
that are exposed by the MCP server.
"""

from __future__ import annotations

try:
    from mcp.types import Tool
except ImportError:
    raise ImportError(
        "MCP server not found. Install with: pip install mcp"
    )


# Parameter models for each tool
class CalculateNatalChartParams:
    """Parameters for calculate_natal_chart."""
    birth_datetime: str
    latitude: float
    longitude: float
    elevation: float = 0.0


class GetPlanetPositionsParams:
    """Parameters for get_planet_positions."""
    datetime: str
    planets: list[str] | None = None


class GetHousesParams:
    """Parameters for get_houses."""
    chart_data: dict[str, Any]


class PlanetPositionInput:
    """Input model for a planet position."""
    longitude: float
    sign: str | None = None
    degree_in_sign: float | None = None


class NatalChartInput:
    """Input model for a natal chart (for transit calculations)."""
    birth_datetime: str
    latitude: float
    longitude: float
    planets: dict[str, PlanetPositionInput]


class CalculateAspectsParams:
    """Parameters for calculate_aspects."""
    chart_data: dict[str, Any]


class CalculateTransitsParams:
    """Parameters for calculate_transits."""
    natal_chart_id: str | None = None
    natal_chart: dict[str, Any] | None = None
    current_datetime: str | None = None


class ScanTransitsParams:
    """Parameters for scan_transits."""
    natal_chart_id: str | None = None
    natal_chart: dict[str, Any] | None = None
    start_date: str
    end_date: str
    min_significance: float = 0.1
    max_results: int | None = None
    house_system: str = "Whole Sign"
    group_by: str | None = None


class LunationScanParams:
    """Parameters for lunation_scan."""
    start_date: str
    end_date: str
    include_void_of_course: bool = True
    natal_chart_id: str | None = None


# Tool definitions
CALCULATE_NATAL_CHART_TOOL = Tool(
    name="calculate_natal_chart",
    description=(
        "Calculate a complete natal chart including planetary positions, "
        "houses, and angles. Returns result_id and preview - use get_result() to retrieve full data. "
        "IMPORTANT: Provide birth datetime with timezone (e.g., '1984-05-10T20:44:00-07:00' for PDT). "
        "Without timezone, the time is assumed to be in local time. "
        "Returns: {result_id, preview, message}"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "birth_datetime": {"type": "string", "description": "Birth datetime in ISO format with timezone"},
            "latitude": {"type": "number", "description": "Latitude of birth location"},
            "longitude": {"type": "number", "description": "Longitude of birth location"},
            "elevation": {"type": "number", "description": "Elevation of birth location (optional, default 0)"},
        },
        "required": ["birth_datetime", "latitude", "longitude"],
    },
)

GET_RESULT_TOOL = Tool(
    name="get_result",
    description=(
        "Retrieve cached data by result_id. "
        "Use this to fetch full chart data after calculate_natal_chart returns a result_id. "
        "The preview contains key highlights (sun/moon/rising signs) for quick decisions."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "result_id": {"type": "string", "description": "The result_id from calculate_natal_chart or other compute tools"},
        },
        "required": ["result_id"],
    },
)

GET_PLANET_POSITIONS_TOOL = Tool(
    name="get_planet_positions",
    description=(
        "Get planetary positions for any date. "
        "Use this to get positions for past, present, or future dates. "
        "For transits at a specific date, use calculate_transits instead. "
        "Returns longitude, latitude, distance, and motion status."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "datetime": {"type": "string", "description": "Date/time in ISO format"},
            "planets": {"type": "array", "items": {"type": "string"}, "description": "List of planet names (optional)"},
        },
        "required": ["datetime"],
    },
)

CALCULATE_ASPECTS_TOOL = Tool(
    name="calculate_aspects",
    description=(
        "Calculate major aspects between planets in a natal chart. "
        "You can pass either: (1) result_id from calculate_natal_chart for lean context, or "
        "(2) chart_data with full chart data (legacy). "
        "When using result_id, the full chart is fetched from cache before calculating aspects. "
        "Returns: list of aspects with planet names, aspect type, orb, and direction."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "result_id": {"type": "string", "description": "Result ID from calculate_natal_chart"},
            "chart_data": {"type": "object", "description": "Full chart data from calculate_natal_chart"},
        },
    },
)

CALCULATE_TRANSITS_TOOL = Tool(
    name="calculate_transits",
    description=(
        "Calculate transits comparing planetary positions to a natal chart for any date. "
        "Use this to analyze transits for past events, present moment, or future dates. "
        "You can pass either: (1) natal_chart_id from calculate_natal_chart for lean context, or "
        "(2) natal_chart with full chart data (legacy). "
        "When using natal_chart_id, the full chart is fetched from cache before calculating transits. "
        "The current_datetime parameter defaults to now if not provided, but you can specify any date/time "
        "(e.g., '2022-07-02T00:00:00+00:00' for July 2, 2022 UTC). "
        "Returns transit events sorted by orb (tightest first)."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "natal_chart_id": {"type": "string", "description": "Result ID from calculate_natal_chart"},
            "natal_chart": {"type": "object", "description": "Full chart data from calculate_natal_chart"},
            "current_datetime": {"type": "string", "description": "Date/time for transit calculation"},
        },
    },
)

SCAN_TRANSITS_TOOL = Tool(
    name="scan_transits",
    description=(
        "Scan transits over a date range, finding all significant transit aspects to a natal chart. "
        "Use this instead of calculate_transits when you need: (1) date-range scanning, "
        "(2) exact timing with peak orb windows, or (3) structured JSON output. "
        "Returns transit events sorted by significance score with full sign/degree data for both "
        "transiting and natal planets. "
        "Parameters: start_date, end_date (required); min_significance (optional, 0-1); "
        "max_results (optional, default unbounded); house_system (optional, defaults to whole_sign). "
        "Output includes: exact_timestamp, peak_orb_window, orb_size_at_peak, aspect_type, "
        "transiting_planet (name, sign, degree), natal_planet (name, sign, degree)."
        "Optional: group_by ('house', 'planet', or 'theme') to return one event per group."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "natal_chart_id": {"type": "string", "description": "Result ID from calculate_natal_chart"},
            "natal_chart": {"type": "object", "description": "Full chart data from calculate_natal_chart"},
            "start_date": {"type": "string", "description": "Start date for scan in ISO format"},
            "end_date": {"type": "string", "description": "End date for scan in ISO format"},
            "min_significance": {"type": "number", "description": "Minimum significance score (optional, default 0.1)"},
            "max_results": {"type": "integer", "description": "Maximum number of results (optional)"},
            "house_system": {"type": "string", "description": "House system name (optional, default 'Whole Sign')"},
            "group_by": {"type": "string", "description": "Group events by 'house', 'planet', or 'theme' (optional)"},
        },
        "required": ["start_date", "end_date"],
    },
)

GET_HOUSES_TOOL = Tool(
    name="get_houses",
    description=(
        "Get house cusp positions for a chart. "
        "Use calculate_natal_chart instead for full chart analysis."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "chart_data": {"type": "object", "description": "Chart data from calculate_natal_chart"},
        },
    },
)

GET_CURRENT_TIME_TOOL = Tool(
    name="get_current_time",
    description=(
        "Get the current UTC date and time. "
        "Use this to help track the correct date when making other tool calls."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
    },
)

CALCULATE_PLANET_ASPECT_TOOL = Tool(
    name="calculate_planet_aspect",
    description=(
        "Calculate the exact aspect between two planetary positions. "
        "Input: two planetary longitudes in degrees (0-360). "
        "Returns: aspect type, exact angle, orb, and whether it's applying or separating."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "planet1_name": {"type": "string", "description": "Name of first planet"},
            "planet1_longitude": {"type": "number", "description": "Longitude of first planet (0-360)"},
            "planet2_name": {"type": "string", "description": "Name of second planet"},
            "planet2_longitude": {"type": "number", "description": "Longitude of second planet (0-360)"},
        },
        "required": ["planet1_name", "planet1_longitude", "planet2_name", "planet2_longitude"],
    },
)

LUNATION_SCAN_TOOL = Tool(
    name="lunation_scan",
    description=(
        "Scan lunar phases and void-of-course periods over a date range. "
        "Input: start_date, end_date. "
        "Returns: moon phases and void-of-course periods with dates."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "Start date in ISO format"},
            "end_date": {"type": "string", "description": "End date in ISO format"},
            "include_void_of_course": {"type": "boolean", "description": "Include void-of-course periods (optional)"},
            "natal_chart_id": {"type": "string", "description": "Result ID from calculate_natal_chart (optional)"},
        },
        "required": ["start_date", "end_date"],
    },
)

# List of all tools for server initialization
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
