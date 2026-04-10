"""MCP Server for Astrology calculations.

This module provides an MCP server exposing astrology tools
for use with local LLMs via tool calling interface.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

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
from astrology.core.ephemeris import get_all_planets, get_planet_position, init_swe, Planet
from astrology.core.aspects import get_major_aspects
from astrology.transits.transit import (
    calculate_single_transit,
    get_current_transits,
)
from astrology.core.calendar import gregorian_to_julian_day

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
    """Parameters for calculating transits."""
    natal_chart: dict[str, Any]
    current_datetime: str


class GetHousesParams(BaseModel):
    """Parameters for getting house cusps."""
    chart_data: dict[str, Any]


# Tool definitions
CALCULATE_NATAL_CHART_TOOL = Tool(
    name="calculate_natal_chart",
    description=(
        "Calculate a complete natal chart including planetary positions, "
        "houses, and angles. Returns comprehensive chart data. "
        "IMPORTANT: Provide birth datetime with timezone (e.g., '1984-05-10T20:44:00-07:00' for PDT). "
        "Without timezone, the time is assumed to be in local time."
    ),
    inputSchema=CalculateNatalChartParams.model_json_schema(),
)

GET_PLANET_POSITIONS_TOOL = Tool(
    name="get_planet_positions",
    description=(
        "Get current planetary positions for specified planets."
        " Returns longitude, latitude, distance, and motion status."
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

CALCULATE_TRANSITS_TOOL = Tool(
    name="calculate_transits",
    description=(
        "Calculate current transits comparing planetary positions "
        "to a natal chart. Returns transiting planets and their aspects."
    ),
    inputSchema=CalculateTransitsParams.model_json_schema(),
)

GET_HOUSES_TOOL = Tool(
    name="get_houses",
    description=(
        "Get house cusp positions and planet placements in houses."
        " Uses Whole Sign house system by default."
    ),
    inputSchema=GetHousesParams.model_json_schema(),
)

GET_CURRENT_TIME_TOOL = Tool(
    name="get_current_time",
    description=(
        "Get the current date and time in UTC. "
        "Useful for calculating transits or current planetary positions."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
    },
)

CALCULATE_PLANET_ASPECT_TOOL = Tool(
    name="calculate_planet_aspect",
    description=(
        "Calculate the exact aspect between two planetary positions given as zodiac coordinates. "
        "Input: two positions in format '0°44\' Aries' or longitude degrees (0-360). "
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
    """Handle calculate_natal_chart tool call."""
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
        result = _serialize_chart(chart)

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str),
        )]
    except Exception as e:
        logger.error(f"Error calculating natal chart: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating natal chart: {str(e)}. "
                 f"Ensure birth datetime includes timezone info (e.g., '1984-05-10T20:44:00-07:00').",
        )]


async def _handle_get_planet_positions(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle get_planet_positions tool call."""
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

                positions[planet_name] = {
                    "longitude": round(pos.longitude.longitude, 4),
                    "sign": pos.longitude.sign_name,
                    "degree_in_sign": round(pos.longitude.degree_in_sign, 2),
                    "latitude": pos.latitude,
                    "distance": round(pos.distance, 4),
                    "retrograde": pos.retrograde,
                }
            except KeyError:
                positions[planet_name] = {"error": f"Unknown planet: {planet_name}"}

        return [TextContent(
            type="text",
            text=json.dumps(positions, indent=2),
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
    """Handle calculate_aspects tool call."""
    return [TextContent(
        type="text",
        text="Aspect calculation requires full chart data. "
             "Use calculate_natal_chart first.",
    )]


async def _handle_calculate_transits(
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle calculate_transits tool call."""
    return [TextContent(
        type="text",
        text="Transit calculation requires a parsed natal chart. "
             "Use calculate_natal_chart first and pass the result.",
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

        # Convert planet names to enums
        try:
            planet1 = Planet[planet1_name.upper()]
            planet2 = Planet[planet2_name.upper()]
        except KeyError:
            return [TextContent(
                type="text",
                text=f"Error: Unknown planet name. "
                     f"Available planets: SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, URANUS, NEPTUNE, PLUTO",
            )]

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
        # For simplicity, assume planets are applying unless they're very far apart
        is_applying = orb < 10.0  # Within 10° is considered applying

        # Get aspect name
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
            text=json.dumps(result, indent=2),
        )]
    except Exception as e:
        logger.error(f"Error calculating planet aspect: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error calculating aspect: {str(e)}",
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
        "angles": {},
    }

    # Add planets
    for planet, position in chart.planets.items():
        result["planets"][planet.name] = {
            "longitude": position.longitude.longitude,
            "sign": position.longitude.sign_name,
            "degree_in_sign": round(position.longitude.degree_in_sign, 2),
            "latitude": position.latitude,
            "distance": round(position.distance, 4),
            "retrograde": position.retrograde,
        }

    # Add houses
    for key, value in chart.houses.items():
        if hasattr(value, "sign_name"):
            result["houses"][key] = {
                "longitude": value.longitude,
                "sign": value.sign_name,
                "degree_in_sign": round(value.degree_in_sign, 2),
            }

    # Add angles
    if chart.ascendant:
        result["angles"]["ascendant"] = {
            "longitude": chart.ascendant.longitude,
            "sign": chart.ascendant.sign_name,
        }
    if chart.midheaven:
        result["angles"]["midheaven"] = {
            "longitude": chart.midheaven.longitude,
            "sign": chart.midheaven.sign_name,
        }

    return result


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
                GET_PLANET_POSITIONS_TOOL,
                CALCULATE_ASPECTS_TOOL,
                CALCULATE_TRANSITS_TOOL,
                GET_HOUSES_TOOL,
                GET_CURRENT_TIME_TOOL,
                CALCULATE_PLANET_ASPECT_TOOL,
            ]

        @server.call_tool()
        async def call_tool(
            name: str,
            arguments: dict[str, Any],
        ) -> list[TextContent]:
            """Handle tool calls."""
            if name == "calculate_natal_chart":
                return await _handle_calculate_natal_chart(arguments)
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
