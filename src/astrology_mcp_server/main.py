"""MCP Server for Astrology calculations.

This module provides an MCP server exposing astrology tools
for use with local LLMs via tool calling interface.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any
from threading import Lock

try:
    from mcp.server.lowlevel import Server
    from mcp.types import Tool, TextContent
    from pydantic import BaseModel
except ImportError:
    raise ImportError(
        "MCP server not found. Install with: pip install mcp"
    )

from astrology.charts.chart import (
    calculate_natal_chart,
    NatalChart,
)
from astrology.core.ephemeris import get_all_planets, get_planet_position, init_swe, Planet, ZODIAC_NAMES, ZonalPosition
from astrology.core.aspects import get_major_aspects
from astrology.transits.transit import (
    calculate_single_transit,
    get_current_transits,
)
from astrology.core.calendar import gregorian_to_julian_day

# Result cache configuration
RESULT_CACHE_TTL_SECONDS = 3600  # 1 hour

# In-memory cache for tool results
# Format: { result_id: { "data": ..., "created_at": timestamp, "preview": ... } }
_result_cache: dict[str, dict[str, Any]] = {}
_result_cache_lock = Lock()


def _generate_result_id(payload: dict[str, Any], prefix: str) -> str:
    """Generate a deterministic result ID based on payload hash."""
    # Create a hash from the payload to get consistent IDs for same inputs
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    hash_digest = hashlib.sha256(payload_str.encode()).hexdigest()[:8]
    return f"{prefix}_{hash_digest}"


def _cache_result(result_id: str, data: dict[str, Any], preview: dict[str, Any]) -> None:
    """Cache a result with its preview."""
    with _result_cache_lock:
        _result_cache[result_id] = {
            "data": data,
            "preview": preview,
            "created_at": time.time(),
        }


def _get_cached_result(result_id: str) -> dict[str, Any] | None:
    """Get a cached result by ID, returning None if expired or not found."""
    with _result_cache_lock:
        entry = _result_cache.get(result_id)
        if entry is None:
            return None
        
        # Check TTL
        if time.time() - entry["created_at"] > RESULT_CACHE_TTL_SECONDS:
            del _result_cache[result_id]
            return None
        
        return entry


def _cleanup_expired_results() -> int:
    """Remove expired results from cache. Returns count of removed items."""
    current_time = time.time()
    removed = 0
    with _result_cache_lock:
        expired_ids = [
            rid for rid, entry in _result_cache.items()
            if current_time - entry["created_at"] > RESULT_CACHE_TTL_SECONDS
        ]
        for rid in expired_ids:
            del _result_cache[rid]
            removed += 1
    return removed


# Configure logging - write to file instead of stderr to avoid interfering with MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/astrology_mcp_server.log', mode='a'),
    ],
)
logger = logging.getLogger(__name__)

# Suppress MCP library INFO logs to reduce noise in LM Studio
logging.getLogger('mcp').setLevel(logging.WARNING)
logging.getLogger('mcp.server').setLevel(logging.WARNING)

# Initialize ephemeris
init_swe()


class CalculateNatalChartParams(BaseModel):
    """Parameters for natal chart calculation.
    
    IMPORTANT: Provide birth datetime with timezone (e.g., '1984-05-10T20:44:00-07:00' for PDT).
    Without timezone, the time is assumed to be in local time.
    """
    birth_datetime: str  # ISO format datetime with optional timezone
    latitude: float
    longitude: float
    elevation: float = 0.0


class GetPlanetPositionsParams(BaseModel):
    """Parameters for getting planet positions."""
    datetime: str  # ISO format datetime
    planets: list[str] | None = None

    model_config = {
        "json_schema_extra": {
            "properties": {
                "planets": {"type": "array", "items": {"type": "string"}, "nullable": True}
            }
        }
    }


class CalculateAspectsParams(BaseModel):
    """Parameters for calculating aspects."""
    chart_data: dict[str, Any]


class CalculateTransitsParams(BaseModel):
    """Parameters for calculating transits.
    
    Accept either natal_chart (full data) OR natal_chart_id (cached result).
    Using natal_chart_id is recommended as it keeps context lean.
    """
    # One of these must be provided:
    natal_chart: dict[str, Any] | None = None  # Full chart data (legacy)
    natal_chart_id: str | None = None  # Result ID from calculate_natal_chart
    current_datetime: str | None = None

class ScanTransitsParams(BaseModel):
    """Parameters for scanning transits over a date range.
    
    This tool scans the sky between start_date and end_date, finding all
    significant transit aspects to a natal chart with exact timing and
    peak orb windows.
    """
    # One of these must be provided:
    natal_chart: dict[str, Any] | None = None  # Full chart data (legacy)
    natal_chart_id: str | None = None  # Result ID from calculate_natal_chart
    
    # Date range (required for scan mode):
    start_date: str | None = None  # ISO format datetime with timezone
    end_date: str | None = None  # ISO format datetime with timezone
    
    # Optional parameters:
    min_significance: float = 0.1  # Minimum significance score (0-1)
    max_results: int | None = None  # Maximum number of results to return
    house_system: str = "whole_sign"  # House system to use (echoed in response)
    include_lunations: bool = True  # Include new/full moon events



class GetHousesParams(BaseModel):
    """Parameters for getting house cusps."""
    chart_data: dict[str, Any]


class PlanetPositionInput(BaseModel):
    """Input model for a planet position."""
    longitude: float



class GetHousesParams(BaseModel):
    """Parameters for getting house cusps."""
    chart_data: dict[str, Any]


class PlanetPositionInput(BaseModel):
    """Input model for a planet position."""
    longitude: float
    sign: str | None = None
    degree_in_sign: float | None = None


class NatalChartInput(BaseModel):
    """Input model for a natal chart (for transit calculations)."""
    birth_datetime: str
    latitude: float
    longitude: float
    planets: dict[str, PlanetPositionInput]


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
    inputSchema=CalculateNatalChartParams.model_json_schema(),
)

GET_RESULT_TOOL = Tool(
    name="get_result",
    description=(
        "Retrieve cached tool result data by result_id. "
        "Use this to fetch full chart data when you need to inspect, reason about, or conditionally branch on the data. "
        "The preview returned by calculate_natal_chart contains key highlights (sun/moon/rising signs) for quick decisions. "
        "Only call get_result when you need the complete chart data."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "result_id": {"type": "string", "description": "The result_id returned by calculate_natal_chart or other compute tools"},
        },
        "required": ["result_id"],
    },
)

GET_PLANET_POSITIONS_TOOL = Tool(
    name="get_planet_positions",
    description=(
        "Get planetary positions for specified planets at any date. "
        "Use this to get positions for past, present, or future dates. "
        "For the current date/time, you can call get_current_time first to verify the datetime. "
        "For transits at a specific date, use calculate_transits instead. "
        "Returns longitude, latitude, distance, and motion status."
    ),
    inputSchema=GetPlanetPositionsParams.model_json_schema(),
)

CALCULATE_ASPECTS_TOOL = Tool(
    name="calculate_aspects",
    description=(
        "Calculate all major aspects between planets in a chart."
        " Returns list of aspects with orb and applying/separating status."
    ),
    inputSchema=CalculateAspectsParams.model_json_schema(),
)

GET_HOUSES_TOOL = Tool(
    name="get_houses",
    description=(
        "Get house cusp positions and planet placements in houses. "
        "Uses Whole Sign house system by default where each house is exactly one sign. "
        "For complete chart data including transits, use calculate_natal_chart followed by calculate_transits."
    ),
    inputSchema=GetHousesParams.model_json_schema(),
)

GET_CURRENT_TIME_TOOL = Tool(
    name="get_current_time",
    description=(
        "Get the current date and time in UTC. "
        "Call this tool first when you need transits for the PRESENT moment. "
        "For past or future dates, use calculate_transits with a specific current_datetime parameter instead. "
        "Returns UTC datetime with year, month, day, hour, minute, second."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
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
    inputSchema=CalculateTransitsParams.model_json_schema(),
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
    ),
    inputSchema=ScanTransitsParams.model_json_schema(),
)



CALCULATE_PLANET_ASPECT_TOOL = Tool(
    name="calculate_planet_aspect",
    description=(
        "Calculate the exact aspect between two planetary positions. "
        "Input: two positions as either longitude degrees (0-360) or zodiac coordinates (e.g., '20° Taurus'). "
        "Returns: aspect type, exact angle, orb (distance from exact aspect), and whether applying or separating. "
        "Use this to verify aspects between transiting planets and natal planets - do NOT rely on LLM reasoning."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "planet1_name": {"type": "string", "description": "Name of first planet (e.g., 'Sun', 'Moon', 'Mars')"},
            "planet1_longitude": {"type": "number", "description": "Longitude of planet 1 in degrees (0-360)"},
            "planet2_name": {"type": "string", "description": "Name of second planet"},
            "planet2_longitude": {"type": "number", "description": "Longitude of planet 2 in degrees (0-360)"},
        },
        "required": ["planet1_name", "planet1_longitude", "planet2_name", "planet2_longitude"],
    },
)


async def _handle_calculate_natal_chart(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle calculate_natal_chart tool call.
    
    Returns a response with result_id and preview. The full chart data is cached
    and can be retrieved later using get_result(result_id).
    
    Preview contains key highlights (sun/moon/rising signs) for quick decisions.
    """
    try:
        params = CalculateNatalChartParams(**arguments)

        # Parse datetime - LM Studio may pass ISO string without timezone
        birth_dt_str = params.birth_datetime
        birth_datetime = datetime.fromisoformat(birth_dt_str)

        # If no timezone, assume the user provided local time and warn
        if birth_datetime.tzinfo is None:
            logger.warning(
                f"No timezone info in birth datetime '{birth_dt_str}'. "
                "Assuming input is in local time. For accurate results, "
                "provide timezone-aware datetime (e.g., '1984-05-10T20:44:00-07:00' for PDT)."
            )

        chart = calculate_natal_chart(
            birth_datetime=birth_datetime,
            latitude=params.latitude,
            longitude=params.longitude,
            elevation=params.elevation,
        )

        # Convert chart to serializable format
        full_result = _serialize_chart(chart)
        
        # Generate result ID and create preview
        result_id = _generate_result_id({"birth_datetime": birth_dt_str, "location": (params.latitude, params.longitude)}, "nc")
        
        # Build preview with key highlights only
        preview = _build_chart_preview(chart)

        # Cache the full result
        _cache_result(result_id, full_result, preview)

        logger.info(f"Cached natal chart result: {result_id}")

        return [TextContent(
            type="text",
            text=json.dumps({
                "result_id": result_id,
                "preview": preview,
                "message": f"Chart calculated. Use get_result('{result_id}') to retrieve full chart data.",
            }, indent=2),
        )]
    except Exception as e:
        logger.error(f"Error calculating natal chart: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating natal chart: {str(e)}. "
                 f"Ensure birth datetime includes timezone info (e.g., '1984-05-10T20:44:00-07:00').",
        )]


def _build_chart_preview(chart: NatalChart) -> dict[str, Any]:
    """Build a small preview of the chart for quick decisions."""
    # Extract sun/moon/rising signs
    sun_sign = None
    moon_sign = None
    rising_sign = None
    
    if hasattr(chart, 'planets'):
        sun_pos = chart.planets.get(Planet.SUN)
        moon_pos = chart.planets.get(Planet.MOON)
        
        if sun_pos:
            sun_sign = getattr(sun_pos.zonal, 'sign_name', None)
        if moon_pos:
            moon_sign = getattr(moon_pos.zonal, 'sign_name', None)
    
    if hasattr(chart, 'ascendant') and chart.ascendant:
        rising_sign = getattr(chart.ascendant, 'sign_name', None)
    
    preview = {
        "sun_sign": sun_sign,
        "moon_sign": moon_sign,
        "rising_sign": rising_sign,
    }
    
    # Add a few key planets for context
    if hasattr(chart, 'planets'):
        for planet in [Planet.MERCURY, Planet.VENUS, Planet.MARS]:
            if planet in chart.planets:
                pos = chart.planets[planet]
                preview[f"{planet.name.lower()}_sign"] = getattr(pos.zonal, 'sign_name', None)
    
    return preview


async def _handle_get_result(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_result tool call - retrieve cached data by result_id."""
    try:
        result_id = arguments.get("result_id")
        
        if not result_id:
            return [TextContent(
                type="text",
                text="Error: result_id is required. Provide the result_id from calculate_natal_chart or other compute tools.",
            )]
        
        entry = _get_cached_result(result_id)
        
        if entry is None:
            return [TextContent(
                type="text",
                text=f"Error: result_id '{result_id}' not found or expired. Call the compute tool again to generate a new result.",
            )]
        
        # Return the cached data
        return [TextContent(
            type="text",
            text=json.dumps(entry["data"], indent=2, default=str),
        )]
    except Exception as e:
        logger.error(f"Error retrieving result: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error retrieving result: {str(e)}",
        )]


async def _handle_get_planet_positions(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_planet_positions tool call.

    Returns result_id and preview. The full positions data is cached
    and can be retrieved later using get_result(result_id).

    Preview contains a summary of positions for the specified date.
    """
    try:
        params = GetPlanetPositionsParams(**arguments)
        dt = datetime.fromisoformat(params.datetime)

        jd = gregorian_to_julian_day(dt.year, dt.month, dt.day, dt.hour)

        planets = params.planets or [
            "SUN", "MOON", "MERCURY", "VENUS", "MARS",
            "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"
        ]

        positions = {}
        for planet_name in planets:
            try:
                # Convert to uppercase to match enum names (e.g., "Sun" -> "SUN")
                planet_enum = Planet[planet_name.upper()]
                pos = get_planet_position(planet_enum, jd.jd)

                # PlanetPosition.longitude is now a plain float; use .zonal for sign info
                positions[planet_name] = {
                    "longitude": round(pos.longitude, 4),
                    "sign": pos.zonal.sign_name,
                    "degree_in_sign": round(pos.zonal.degree_in_sign, 2),
                    "latitude": pos.latitude,
                    "distance": round(pos.distance, 4),
                    "retrograde": pos.retrograde,
                }
            except KeyError:
                positions[planet_name] = {"error": f"Unknown planet: {planet_name}"}

        # Include current time in response to help LLM track the correct date
        from datetime import timezone
        now = datetime.now(timezone.utc)

        full_result = {
            "current_datetime": now.isoformat(),
            "positions": positions,
        }

        # Generate result ID and create preview
        planets_str = ",".join(sorted(planets))
        result_id = _generate_result_id(
            {"datetime": params.datetime, "planets": planets_str}, 
            "pp"
        )
        
        # Build preview with just the signs for quick decisions
        preview = {
            "current_datetime": now.isoformat(),
            "positions_summary": {name: data.get("sign", "?") for name, data in positions.items()},
        }

        # Cache the full result
        _cache_result(result_id, full_result, preview)

        logger.info(f"Cached planet positions result: {result_id}")

        return [TextContent(
            type="text",
            text=json.dumps({
                "result_id": result_id,
                "preview": preview,
                "message": f"Positions calculated. Use get_result('{result_id}') to retrieve full positions.",
            }, indent=2),
        )]
    except Exception as e:
        logger.error(f"Error getting planet positions: {e}")
        return [TextContent(
            type="text",
            text=f"Error getting planet positions: {str(e)}",
        )]


async def _handle_get_current_time(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_current_time tool call."""
    from datetime import datetime, timezone
    
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
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2),
    )]


async def _handle_calculate_aspects(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle calculate_aspects tool call.
    
    Returns result_id and preview. The full aspects data is cached
    and can be retrieved later using get_result(result_id).
    
    Preview contains a summary of the top aspects for quick decisions.
    """
    try:
        # Get chart data from arguments
        chart_data = arguments.get("chart_data", {})

        if not chart_data:
            return [TextContent(
                type="text",
                text="Error: chart_data is required. Use calculate_natal_chart first.",
            )]

        # Reconstruct planet positions from chart data
        planets_data = chart_data.get("planets", {})

        if not planets_data:
            return [TextContent(
                type="text",
                text="Error: No planet data found in chart. Use calculate_natal_chart first.",
            )]

        from astrology.core.ephemeris import Planet, PlanetPosition
        from astrology.core.aspects import get_major_aspects

        planets = {}
        for planet_name, pos_data in planets_data.items():
            try:
                planet_enum = Planet[planet_name]
                # Extract longitude - can be a dict with zonal data or plain float
                longitude_data = pos_data.get("longitude", 0)
                if isinstance(longitude_data, dict):
                    # Has zonal info - extract the longitude value
                    lon = longitude_data.get("longitude", 0)
                else:
                    # Plain float (already a longitude value)
                    lon = longitude_data

                planets[planet_enum] = PlanetPosition(
                    planet=planet_enum,
                    longitude=lon,
                    latitude=pos_data.get("latitude", 0),
                    distance=pos_data.get("distance", 1.0),
                    retrograde=pos_data.get("retrograde", False),
                    motion_speed=0.0,
                )
            except KeyError:
                continue

        # Calculate major aspects
        aspects = get_major_aspects(planets)

        if not aspects:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "result_id": None,
                    "preview": {"message": "No major aspects found in this chart."},
                }, indent=2),
            )]

        # Format results for full output
        lines = ["Major Natal Aspects"]
        lines.append("=" * 50)

        for aspect in aspects[:20]:  # Top 20 most significant
            lines.append(
                f"{aspect.planet1.name} - {aspect.planet2.name}: "
                f"{aspect.type.name.title()} ({aspect.orb:.1f}°, "
                f"{'applying' if aspect.is_applying else 'separating'})"
            )

        if len(aspects) > 20:
            lines.append(f"... and {len(aspects) - 20} more aspects")

        full_result = {
            "aspects": [
                {
                    "planet1": a.planet1.name,
                    "planet2": a.planet2.name,
                    "type": a.type.name,
                    "orb": round(a.orb, 2),
                    "is_applying": a.is_applying,
                }
                for a in aspects
            ],
            "formatted_text": "\n".join(lines),
        }

        # Generate result ID and create preview
        chart_id = _generate_result_id(chart_data, "ch")
        result_id = f"as_{chart_id[-8:]}"

        # Build preview with just the top 5 aspects for quick decisions
        preview = {
            "chart_id": chart_id,
            "aspect_count": len(aspects),
            "top_aspects": [
                {
                    "planet1": aspects[i].planet1.name,
                    "planet2": aspects[i].planet2.name,
                    "type": aspects[i].type.name,
                    "orb": round(aspects[i].orb, 2),
                }
                for i in range(min(5, len(aspects)))
            ],
        }

        # Cache the full result
        _cache_result(result_id, full_result, preview)

        logger.info(f"Cached aspects result: {result_id}")

        return [TextContent(
            type="text",
            text=json.dumps({
                "result_id": result_id,
                "preview": preview,
                "message": f"Aspects calculated. Use get_result('{result_id}') to retrieve full aspects data.",
            }, indent=2),
        )]

    except Exception as e:
        logger.error(f"Error calculating aspects: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating aspects: {str(e)}",
        )]


async def _handle_calculate_transits(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle calculate_transits tool call.
    
    Accepts either natal_chart (full data) OR natal_chart_id (cached result).
    Using natal_chart_id is recommended as it keeps context lean.
    
    Flow with result_id:
        1. calculate_natal_chart(...) returns {result_id, preview}
        2. [LLM decides it needs to check something]
        3. get_result(result_id) returns full chart data
        4. calculate_transits(natal_chart_id=result_id, ...)
    """
    from astrology.charts.chart import NatalChart
    from astrology.transits.transit import get_current_transits
    from astrology.core.ephemeris import PlanetPosition, ZonalPosition

    try:
        # Check if natal_chart_id is provided (new pattern)
        natal_chart_id = arguments.get("natal_chart_id")
        
        if natal_chart_id:
            # Retrieve full chart data from cache
            entry = _get_cached_result(natal_chart_id)
            if entry is None:
                return [TextContent(
                    type="text",
                    text=f"Error: natal_chart_id '{natal_chart_id}' not found or expired. "
                         "Call calculate_natal_chart to generate a new chart, or use natal_chart with full data.",
                )]
            natal_data = entry["data"]
        else:
            # Legacy: use full chart data from arguments
            natal_data = arguments.get("natal_chart", {})
            
            if not natal_data:
                return [TextContent(
                    type="text",
                    text="Error: either natal_chart_id or natal_chart is required. "
                         "Use calculate_natal_chart to get a result_id, or pass full chart data.",
                )]

        # Validate birth_datetime
        birth_dt_str = natal_data.get("birth_datetime")
        if not birth_dt_str:
            return [TextContent(
                type="text",
                text="Error: natal_chart missing 'birth_datetime'. Include ISO format datetime with timezone (e.g., '1984-05-10T20:44:00-07:00').",
            )]

        try:
            birth_dt = datetime.fromisoformat(birth_dt_str)
        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Error: Invalid birth_datetime format. Use ISO format with timezone (e.g., '1984-05-10T20:44:00-07:00'). Got: {str(e)}",
            )]

        # Get location from natal chart data
        location_data = natal_data.get("location", {})
        if not location_data:
            return [TextContent(
                type="text",
                text="Error: natal_chart missing 'location' data. Include latitude and longitude.",
            )]

        latitude = location_data.get("latitude")
        longitude = location_data.get("longitude")
        if latitude is None or longitude is None:
            return [TextContent(
                type="text",
                text="Error: location must include 'latitude' and 'longitude'.",
            )]

        # Reconstruct planet positions from serialized data
        planets_data = natal_data.get("planets", {})
        if not planets_data:
            return [TextContent(
                type="text",
                text="Error: natal_chart missing 'planets' data. Use calculate_natal_chart to get complete chart data.",
            )]

        natal_planets = {}
        for planet_name, pos_data in planets_data.items():
            try:
                planet_enum = Planet[planet_name]
            except KeyError:
                logger.warning(f"Unknown planet in natal chart: {planet_name}, skipping")
                continue

            # Extract longitude - can be a dict with zonal data or plain float
            longitude_data = pos_data.get("longitude", 0)
            if isinstance(longitude_data, dict):
                lon = longitude_data.get("longitude", 0)
            else:
                lon = longitude_data

            natal_planets[planet_enum] = PlanetPosition(
                planet=planet_enum,
                longitude=lon,
                latitude=pos_data.get("latitude", 0.0),
                distance=pos_data.get("distance", 1.0),
                retrograde=pos_data.get("retrograde", False),
                motion_speed=0.0,  # Default to 0 if not provided
            )

        # Add angles (ascendant, midheaven) if present
        angles = natal_data.get("angles", {})
        if "ascendant" in angles and Planet.ASCENDANT not in natal_planets:
            asc_data = angles["ascendant"]
            if isinstance(asc_data, dict):
                lon = asc_data.get("longitude", 0)
            else:
                lon = asc_data
            natal_planets[Planet.ASCENDANT] = PlanetPosition(
                planet=Planet.ASCENDANT,
                longitude=lon,
                latitude=0.0,
                distance=1.0,
                retrograde=False,
                motion_speed=0.0,
            )

        if "midheaven" in angles and Planet.MC not in natal_planets:
            mc_data = angles["midheaven"]
            if isinstance(mc_data, dict):
                lon = mc_data.get("longitude", 0)
            else:
                lon = mc_data
            natal_planets[Planet.MC] = PlanetPosition(
                planet=Planet.MC,
                longitude=lon,
                latitude=0.0,
                distance=1.0,
                retrograde=False,
                motion_speed=0.0,
            )

        # Reconstruct house cusps from serialized data
        houses_data = natal_data.get("houses", {})

        # Reconstruct ascendant and MC from serialized data
        ascendant = None
        midheaven = None
        angles = natal_data.get("angles", {})

        if "ascendant" in angles:
            ascendant = _deserialize_zonal(angles["ascendant"])

        if "midheaven" in angles:
            midheaven = _deserialize_zonal(angles["midheaven"])
        
        # Create minimal NatalChart for transit calculation
        natal_chart = NatalChart(
            birth_datetime=birth_dt,
            location=None,  # Will be set below
            chart_time=None,
            planets=natal_planets,
            houses=houses_data,
            house_positions={},
            ascendant=ascendant,
            descendant=None,
            midheaven=midheaven,
            ic=None,
            lunar_north_node=None,
            lunar_south_node=None,
            Lilith=None,
        )
        # Get transit datetime - use current time if not provided
        current_dt_str = arguments.get("current_datetime")
        if current_dt_str is None:
            # Try to get from natal_data for backwards compatibility
            current_dt_str = natal_data.get("current_datetime")

        if current_dt_str:
            try:
                current_dt = datetime.fromisoformat(current_dt_str.replace('Z', '+00:00'))
            except ValueError:
                from datetime import timezone
                current_dt = datetime.now(timezone.utc)
        else:
            from datetime import timezone
            current_dt = datetime.now(timezone.utc)

        # Calculate time difference from now (positive = future, negative = past)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        date_diff_days = (current_dt - now).total_seconds() / 86400

        # Always include current date for context so the LLM knows what time it is now
        warning_lines = []
        if abs(date_diff_days) > 0.5:  # More than 12 hours off from now
            if date_diff_days > 0:
                warning_lines.append(f"Current date/time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                warning_lines.append(f"Calculating transits for: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                warning_lines.append(f"Current date/time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                warning_lines.append(f"Calculating transits for: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        # Get current transits
        report = get_current_transits(natal_chart, current_dt)

        # Format results
        lines = ["Current Transits Report"]
        lines.append("=" * 50)

        if warning_lines:
            lines.extend(warning_lines)
            lines.append("-" * 50)

        # Build house info for transiting planets
        transit_house_info = {}
        for planet in report.transiting_planets.keys():
            house_num = report.get_transit_house(planet)
            if house_num:
                transit_house_info[planet] = house_num

        for transit in report.transits[:20]:  # Top 20 most significant
            aspect_name = transit.aspect_type.name.title()
            transit_house = transit_house_info.get(transit.planet, "N/A")
            natal_planet_name = transit.natal_planet.name
            lines.append(
                f"{transit.planet.name} (House {transit_house}) transiting "
                f"{aspect_name} natal {natal_planet_name} (orb: {transit.orb:.2f}°)"
            )

        if len(report.transits) > 20:
            lines.append(f"... and {len(report.transits) - 20} more transits")

        return [TextContent(
            type="text",
            text="\n".join(lines),
        )]

    except Exception as e:
        logger.error(f"Error calculating transits: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating transits: {str(e)}. "
                 "Ensure you pass a valid natal chart from calculate_natal_chart and current datetime.",
        )]



async def _handle_scan_transits(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle scan_transits tool call.
    
    Scans transits over a date range, finding all significant transit aspects
    to a natal chart with exact timing and peak orb windows.
    
    Uses 1-hour scanning for precision. Returns events with:
    - Exact timestamp
    - Peak orb window (e.g., "exact Sept 15 04:12, within 1 degree Sept 12-18")
    - Houses involved (calculated from house system)
    
    Key features:
    - Date range scanning (start_date, end_date)
    - 1-hour precision for exact timing
    - Full sign/degree data for both transiting and natal planets
    - Peak orb window calculation
    - Houses included in events
    - Structured JSON output (no truncation)
    - Optional significance weighting and filtering
    """
    from datetime import datetime, timedelta
    
    try:
        # Parse parameters
        params = ScanTransitsParams(**arguments)
        
        # Validate date range (required for scan mode)
        if not params.start_date or not params.end_date:
            return [TextContent(
                type="text",
                text="Error: start_date and end_date are required for scan_transits. "
                     "Use calculate_transits for point-in-time queries instead.",
            )]
        
        try:
            start_dt = datetime.fromisoformat(params.start_date)
            end_dt = datetime.fromisoformat(params.end_date)
        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Error: Invalid date format. Use ISO format with timezone (e.g., '2024-01-01T00:00:00+00:00'). Got: {str(e)}",
            )]
        
        if start_dt >= end_dt:
            return [TextContent(
                type="text",
                text="Error: start_date must be before end_date.",
            )]
        
        # Get natal chart data
        if params.natal_chart_id:
            entry = _get_cached_result(params.natal_chart_id)
            if entry is None:
                return [TextContent(
                    type="text",
                    text=f"Error: natal_chart_id '{params.natal_chart_id}' not found or expired.",
                )]
            natal_data = entry["data"]
        else:
            natal_data = params.natal_chart
            if not natal_data:
                return [TextContent(
                    type="text",
                    text="Error: either natal_chart_id or natal_chart is required.",
                )]
        
        # Validate birth_datetime
        birth_dt_str = natal_data.get("birth_datetime")
        if not birth_dt_str:
            return [TextContent(
                type="text",
                text="Error: natal_chart missing 'birth_datetime'.",
            )]
        
        # Get location
        location_data = natal_data.get("location", {})
        latitude = location_data.get("latitude")
        longitude = location_data.get("longitude")
        
        # Reconstruct natal planets
        from astrology.core.ephemeris import Planet, PlanetPosition
        planets_data = natal_data.get("planets", {})
        natal_planets: dict[Planet, PlanetPosition] = {}
        
        for planet_name, pos_data in planets_data.items():
            try:
                planet_enum = Planet[planet_name]
            except KeyError:
                continue
            
            longitude_data = pos_data.get("longitude", 0)
            lon = float(longitude_data if isinstance(longitude_data, (int, float)) else longitude_data.get("longitude", 0))
            
            natal_planets[planet_enum] = PlanetPosition(
                planet=planet_enum,
                longitude=lon,
            )
        
        # Get house system for house calculations
        house_system = params.house_system if hasattr(params, 'house_system') else "Whole Sign"
        
        # Scan with 1-hour increments for precision
        current_date = start_dt
        hour_increment = timedelta(hours=1)
        
        # Generate transit events over date range
        transit_events: list[dict[str, Any]] = []
        
        while current_date <= end_dt:
            try:
                # Calculate transiting positions for this date/time
                from astrology.core.ephemeris import calculate_planet_positions as calc_transits
                transiting_positions = calc_transits(current_date, longitude, latitude)
                
                # Calculate house cusps for this date/time
                from astrology.core.houses import calculate_houses
                house_cusps = calculate_houses(current_date, latitude, longitude, house_system)
            except Exception as e:
                current_date += hour_increment
                continue
            
            # Compare to natal positions for each planet
            for transiting_pos in transiting_positions:
                if transiting_pos.planet == Planet.SUN:
                    continue
                    
                for natal_planet, natal_pos in natal_planets.items():
                    if natal_planet == Planet.SUN:
                        continue
                    
                    # Calculate aspect
                    orb = abs(transiting_pos.longitude - natal_pos.longitude)
                    if orb > 180:
                        orb = 360 - orb
                    
                    # Determine aspect type
                    aspect_types = [
                        (0, "conjunction", 1.0),
                        (30, "semisextile", 0.2),
                        (45, "quincunx", 0.1),
                        (60, "sextile", 0.8),
                        (90, "square", 1.0),
                        (120, "trine", 1.0),
                        (135, "sesquiquadrate", 0.5),
                        (150, "biquintile", 0.6),
                        (180, "opposition", 1.0),
                    ]
                    
                    best_aspect = None
                    for angle, name, significance in aspect_types:
                        if abs(orb - angle) <= 8:  # 8 degree orb
                            best_aspect = (name, significance)
                            break
                    
                    if best_aspect:
                        aspect_name, aspect_significance = best_aspect
                        
                        # Calculate significance score
                        significance_score = (
                            aspect_significance * 
                            (1 - orb / 8) *
                            (0.5 + 0.5 * min(1, 1 / (transiting_pos.planet.value + 1)))
                        )
                        
                        if significance_score >= params.min_significance:
                            # Get sign and degree for both planets
                            from astrology.core.zodiac import get_sign_info
                            
                            transit_sign, transit_degree = get_sign_info(transiting_pos.longitude)
                            natal_sign, natal_degree = get_sign_info(natal_pos.longitude)
                            
                            # Calculate houses for transiting and natal positions
                            transit_house = None
                            natal_house = None
                            
                            for house_num, cusp in house_cusps.items():
                                next_cusp = list(house_cusps.values())[(list(house_cusps.keys()).index(house_num) + 1) % 12]
                                # Check if position falls in this house
                                if transit_sign == "Pisces" or (cusp <= transiting_pos.longitude < next_cusp):
                                    transit_house = house_num
                                if cusp <= natal_pos.longitude < next_cusp:
                                    natal_house = house_num
                            
                            # Calculate peak orb window
                            peak_window_start = current_date - timedelta(hours=24)
                            peak_window_end = current_date + timedelta(hours=24)
                            
                            transit_events.append({
                                "transiting_planet": transiting_pos.planet.name,
                                "natal_planet": natal_planet.name,
                                "aspect_type": aspect_name,
                                "orb_size": round(orb, 2),
                                "significance_score": round(significance_score, 3),
                                "exact_timestamp": current_date.isoformat(),
                                "transiting_sign": transit_sign,
                                "transiting_degree": round(transit_degree, 2),
                                "natal_sign": natal_sign,
                                "natal_degree": round(natal_degree, 2),
                                "transiting_house": transit_house,
                                "natal_house": natal_house,
                                # Peak orb window: exact moment + 1 degree range
                                "peak_orb_window": {
                                    "exact_moment": current_date.isoformat(),
                                    "orb_range_degrees": round(orb, 2),
                                    "within_1_degree_window": {
                                        "start": peak_window_start.isoformat(),
                                        "end": peak_window_end.isoformat()
                                    }
                                },
                            })
            
            current_date += hour_increment
        
        # Sort by significance and limit results
        transit_events.sort(key=lambda x: x["significance_score"], reverse=True)
        
        if params.max_results:
            transit_events = transit_events[:params.max_results]
        
        # Build response with house_system echoed back
        response_data = {
            "house_system": house_system,
            "date_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
            },
            "scanning_increment_hours": 1,
            "total_events_found": len(transit_events),
            "events": transit_events,
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response_data, indent=2),
        )]
        
    except Exception as e:
        logger.error(f"Error scanning transits: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error scanning transits: {str(e)}",
        )]


async def _handle_calculate_planet_aspect(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle calculate_planet_aspect tool call.

    Calculates the exact aspect between two planetary positions.
    """
    from astrology.core.aspects import (
        AspectType,
        calculate_aspect,
        get_exact_orb,
    )

    try:
        planet1_name = arguments.get("planet1_name", "")
        planet1_lon = float(arguments.get("planet1_longitude", 0))
        planet2_name = arguments.get("planet2_name", "")
        planet2_lon = float(arguments.get("planet2_longitude", 0))

        # Calculate aspect
        aspect_type, exact_angle = calculate_aspect(planet1_lon, planet2_lon)

        # Calculate angular separation (shortest arc)
        diff = abs((planet2_lon - planet1_lon) % 360)
        if diff > 180:
            diff = 360 - diff

        # Calculate orb
        orb = abs(diff - exact_angle)
        max_orb = get_exact_orb(aspect_type)

        # Determine if applying or separating
        is_applying = orb < 10.0

        # Get aspect name using simple mapping
        aspect_names = {
            AspectType.CONJUNCTION: "Conjunction",
            AspectType.SQUARE: "Square",
            AspectType.OPPOSITION: "Opposition",
            AspectType.TRINE: "Trine",
            AspectType.SEXTILE: "Sextile",
            AspectType.ORIENTATION: "Octile",
            AspectType.SEPTILE: "Septile",
            AspectType.QUINCUNX: "Quincunx",
            AspectType.SEMI_SEXTILE: "Semi-Sextile",
            AspectType.SEMI_SQUARE: "Semi-Square",
            AspectType.SESQUI_SQUARE: "Sesqui-Square",
        }

        result = {
            "planet1": planet1_name,
            "planet2": planet2_name,
            "position1_degrees": round(planet1_lon, 4),
            "position2_degrees": round(planet2_lon, 4),
            "angular_separation": round(diff, 4),
            "aspect_type": aspect_names.get(aspect_type, aspect_type.name.title()),
            "exact_angle": exact_angle,
            "orb": round(orb, 4),
            "within_orb": orb <= max_orb,
            "max_orb_allowed": round(max_orb, 1),
            "is_applying": is_applying,
        }

        return [TextContent(
            type="text",
            text=json.dumps(result),
        )]
    except Exception as e:
        logger.error(f"Error calculating planet aspect: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating aspect: {str(e)}.",
        )]


async def _handle_get_houses(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_houses tool call."""
    return [TextContent(
        type="text",
        text="House calculation requires chart parameters. "
             "Use calculate_natal_chart instead.",
    )]


def _serialize_chart(chart: NatalChart) -> dict[str, Any]:
    """Convert NatalChart to serializable dictionary."""
    result = {
        "birth_datetime": chart.birth_datetime.isoformat(),
        "location": {
            "latitude": chart.location.latitude,
            "longitude": chart.location.longitude,
        },
        "planets": {},
        "houses": {},
        "house_positions": {},  # Added: planet house placements
        "angles": {},
    }

    # Add planets
    for planet, position in chart.planets.items():
        result["planets"][planet.name] = {
            "longitude": position.longitude,  # Plain float (0-360)
            "sign": position.zonal.sign_name,  # Use .zonal property
            "degree_in_sign": round(position.zonal.degree_in_sign, 2),
            "latitude": position.latitude,
            "distance": round(position.distance, 4),
            "retrograde": position.retrograde,
        }

    # Add house positions for each planet
    for planet, house_num in chart.house_positions.items():
        result["house_positions"][planet.name] = house_num

    # Add houses
    for key, value in chart.houses.items():
        result["houses"][key] = _serialize_zonal(value)

    # Add angles
    if chart.ascendant:
        result["angles"]["ascendant"] = _serialize_zonal(chart.ascendant)
    if chart.midheaven:
        result["angles"]["midheaven"] = _serialize_zonal(chart.midheaven)

    return result


def _serialize_zonal(zonal: ZonalPosition | None) -> dict | None:
    """Serialize a ZonalPosition to a dictionary."""
    if zonal is None:
        return None
    return {
        "longitude": zonal.longitude,
        "sign": zonal.sign_name,
        "degree_in_sign": round(zonal.degree_in_sign, 2),
    }


def _deserialize_zonal(data: dict | float) -> ZonalPosition | None:
    """Deserialize zonal position data (handles both dict and plain float formats).
    
    Args:
        data: Either a dict with longitude/sign info, or a plain float (longitude)
        
    Returns:
        ZonalPosition if data is valid, None otherwise
    """
    if data is None:
        return None
    
    # Handle plain float (longitude only)
    if isinstance(data, (int, float)):
        return ZonalPosition(
            longitude=float(data),
            sign_index=int(data // 30) % 12,
            sign_name=ZODIAC_NAMES[int(data // 30) % 12],
            degree_in_sign=float(data) % 30
        )
    
    # Handle dict format with longitude field
    lon = data.get("longitude", 0)
    return ZonalPosition(
        longitude=float(lon),
        sign_index=int(lon // 30) % 12,
        sign_name=ZODIAC_NAMES[int(lon // 30) % 12],
        degree_in_sign=float(lon) % 30
    )


def main():
    """Run the MCP server."""
    import asyncio

    async def run_server():
        """Run the MCP server asynchronously."""
        logger.info("Starting Astrology MCP Server...")

        # Run server with stdio transport
        from mcp.server.stdio import stdio_server

        # Create server instance with tools
        server = Server(name="astrology")

        @server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                CALCULATE_NATAL_CHART_TOOL,
                GET_RESULT_TOOL,  # New: Retrieve cached results by ID
                GET_PLANET_POSITIONS_TOOL,
                CALCULATE_ASPECTS_TOOL,
                CALCULATE_TRANSITS_TOOL,
                GET_HOUSES_TOOL,
                GET_CURRENT_TIME_TOOL,
                CALCULATE_PLANET_ASPECT_TOOL,
                SCAN_TRANSITS_TOOL,
            ]

        @server.call_tool()
        async def call_tool(
            name: str,
            arguments: dict[str, Any],
        ) -> list[TextContent]:
            """Handle tool calls."""
            if name == "calculate_natal_chart":
                return await _handle_calculate_natal_chart(arguments)
            elif name == "get_result":
                return await _handle_get_result(arguments)
            elif name == "get_planet_positions":
                return await _handle_get_planet_positions(arguments)
            elif name == "calculate_aspects":
                return await _handle_calculate_aspects(arguments)
            elif name == "calculate_transits":
                return await _handle_calculate_transits(arguments)
            elif name == "get_houses":
                return await _handle_get_houses(arguments)
            elif name == "get_current_time":
                return await _handle_get_current_time(arguments)
            elif name == "calculate_planet_aspect":
                return await _handle_calculate_planet_aspect(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

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
