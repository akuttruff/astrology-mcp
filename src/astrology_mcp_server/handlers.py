"""Tool handler functions for Astrology MCP Server.

This module contains all the async handler functions that process
individual tool calls from the MCP server.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

try:
    from mcp.types import TextContent
except ImportError:
    raise ImportError(
        "MCP server not found. Install with: pip install mcp"
    )

from astrology.charts.chart import calculate_natal_chart, NatalChart
from astrology.core.ephemeris import Planet, PlanetPosition, ZonalPosition, ZODIAC_NAMES, get_planet_position
from astrology.core.aspects import get_major_aspects
from astrology.transits.transit import get_current_transits
from .transit_utils import get_aspect_display_name, is_major_aspect
from .transit_timing import interpolate_exact_moment

from .cache import (
    _get_cached_result,
    _get_cached_result_with_reason,
    _cache_result,
    _generate_result_id,
)
from .serializers import _serialize_chart, _build_chart_preview, _deserialize_zonal

# Configure logging
logger = logging.getLogger(__name__)


async def handle_calculate_natal_chart(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle calculate_natal_chart tool call.
    
    Returns a response with result_id and preview. The full chart data is cached
    and can be retrieved later using get_result(result_id).
    
    Preview contains key highlights (sun/moon/rising signs) for quick decisions.
    """
    try:
        from pydantic import BaseModel
        
        class CalculateNatalChartParams(BaseModel):
            birth_datetime: str
            latitude: float
            longitude: float
            elevation: float = 0.0
        
        params = CalculateNatalChartParams(**arguments)
        
        # Parse datetime
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
        # Include birth_datetime, location, and timezone for fully unique keys
        result_id = _generate_result_id(
            {
                "birth_datetime": birth_dt_str,
                "location": (params.latitude, params.longitude),
                "timezone": getattr(params, 'timezone', 'unknown'),
            },
            "nc"
        )
        
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


async def handle_get_result(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_result tool call - retrieve cached data by result_id."""
    try:
        result_id = arguments.get("result_id")
        
        if not result_id:
            return [TextContent(
                type="text",
                text="Error: result_id is required. Provide the result_id from calculate_natal_chart or other compute tools.",
            )]

        entry, reason = _get_cached_result_with_reason(result_id)

        if entry is None:
            if reason == "expired":
                return [TextContent(
                    type="text",
                    text=f"Error: result_id '{result_id}' has expired (TTL: 1 week). Call the compute tool again to generate a new result.",
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: result_id '{result_id}' not found. Please verify the ID or call the compute tool again.",
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


async def handle_get_planet_positions(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_planet_positions tool call.
    
    Returns result_id and preview. The full positions data is cached
    and can be retrieved later using get_result(result_id).
    
    Preview contains a summary of positions for the specified date.
    """
    try:
        from pydantic import BaseModel
        from astrology.core.calendar import gregorian_to_julian_day
        
        class GetPlanetPositionsParams(BaseModel):
            datetime: str
            planets: list[str] | None = None
        
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


async def handle_get_current_time(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_current_time tool call."""
    from datetime import timezone
    
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


async def handle_calculate_aspects(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle calculate_aspects tool call.

    Accepts either chart_data (full data) OR result_id (cached result).
    Using result_id is recommended as it keeps context lean.
    
    Returns result_id and preview. The full aspects data is cached
    and can be retrieved later using get_result(result_id).

    Preview contains a summary of the top aspects for quick decisions.
    """
    try:
        # Check if result_id is provided (new pattern)
        result_id = arguments.get("result_id")
        
        if result_id:
            # Retrieve full chart data from cache
            entry, reason = _get_cached_result_with_reason(result_id)
            if entry is None:
                if reason == "expired":
                    return [TextContent(
                        type="text",
                        text=f"Error: result_id '{result_id}' has expired (TTL: 1 week). "
                             "Please recalculate with calculate_natal_chart, or use chart_data with full data.",
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: result_id '{result_id}' not found. "
                             "Please verify the ID or calculate a new chart with calculate_natal_chart.",
                    )]
            chart_data = entry["data"]
        else:
            # Legacy: use full chart data from arguments
            chart_data = arguments.get("chart_data", {})
            
            if not chart_data:
                return [TextContent(
                    type="text",
                    text="Error: either result_id or chart_data is required. "
                         "Use calculate_natal_chart to get a result_id, or pass full chart data.",
                )]

        # Reconstruct planet positions from chart data
        planets_data = chart_data.get("planets", {})

        if not planets_data:
            return [TextContent(
                type="text",
                text="Error: No planet data found in chart. Use calculate_natal_chart first.",
            )]
        
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
                    motion_speed=pos_data.get("motion_speed", 0.0),  # Use serialized value or default to 0
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


async def handle_calculate_transits(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle calculate_transits tool call.

    Accepts either natal_chart (full data) OR natal_chart_id (cached result).
    Using natal_chart_id is recommended as it keeps context lean.
    """
    try:
        # Check if natal_chart_id is provided (new pattern)
        natal_chart_id = arguments.get("natal_chart_id")

        if natal_chart_id:
            # Retrieve full chart data from cache
            entry, reason = _get_cached_result_with_reason(natal_chart_id)
            if entry is None:
                if reason == "expired":
                    return [TextContent(
                        type="text",
                        text=f"Error: natal_chart_id '{natal_chart_id}' has expired (TTL: 1 week). "
                             "Please recalculate with calculate_natal_chart, or use natal_chart with full data.",
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: natal_chart_id '{natal_chart_id}' not found. "
                             "Please verify the ID or calculate a new chart with calculate_natal_chart.",
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
                motion_speed=pos_data.get("motion_speed", 0.0),  # Use serialized value or default to 0
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
                motion_speed=asc_data.get("motion_speed", 0.0) if isinstance(asc_data, dict) else 0.0,
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
                motion_speed=mc_data.get("motion_speed", 0.0) if isinstance(mc_data, dict) else 0.0,
            )
        
        # Reconstruct house cusps from serialized data
        houses_data = natal_data.get("houses", {})
        
        # Reconstruct ascendant and MC from serialized data
        ascendant = None
        midheaven = None
        
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
            aspect_name = get_aspect_display_name(transit.aspect_type)
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


async def handle_scan_transits(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle scan_transits tool call.
    
    Scans transits over a date range, finding all significant transit aspects
    to a natal chart with exact timing and peak orb windows.
    """
    try:
        from pydantic import BaseModel
        
        class ScanTransitsParams(BaseModel):
            natal_chart_id: str | None = None
            natal_chart: dict[str, Any] | None = None
            start_date: str
            end_date: str
            min_significance: float = 0.1
            max_results: int | None = None
            house_system: str = "Whole Sign"
            group_by: str | None = None
        
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
            entry, reason = _get_cached_result_with_reason(params.natal_chart_id)
            if entry is None:
                if reason == "expired":
                    return [TextContent(
                        type="text",
                        text=f"Error: natal_chart_id '{params.natal_chart_id}' has expired (TTL: 1 week). "
                             "Please recalculate the natal chart with calculate_natal_chart.",
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error: natal_chart_id '{params.natal_chart_id}' not found. "
                             "Please verify the ID or calculate a new natal chart with calculate_natal_chart.",
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
                latitude=pos_data.get("latitude", 0.0),
                distance=pos_data.get("distance", 1.0),
                retrograde=pos_data.get("retrograde", False),
                motion_speed=pos_data.get("motion_speed", 0.0),  # Use serialized value or default to 0
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
                motion_speed=pos_data.get("motion_speed", 0.0),  # Use serialized value or default to 0
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
                motion_speed=pos_data.get("motion_speed", 0.0),  # Use serialized value or default to 0
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
                from astrology.core.ephemeris import get_all_planets
                from astrology.core.calendar import gregorian_to_julian_day
                jd = gregorian_to_julian_day(current_date.year, current_date.month, current_date.day, current_date.hour)
                transiting_positions = list(get_all_planets(jd.jd).values())

                # Calculate house cusps for this date/time
                from astrology.core.ephemeris import calculate_houses
                house_cusps = calculate_houses(jd.jd, latitude, longitude, house_system)
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
                            # Interpolate to find the exact moment of closest approach
                            exact_time, exact_orb = interpolate_exact_moment(
                                transiting_pos.planet,
                                natal_pos,
                                current_date - timedelta(hours=12),
                                current_date + timedelta(hours=12)
                            )
                            
                            # Get sign and degree from zonal position
                            transit_sign = transiting_pos.zonal.sign_name
                            transit_degree = transiting_pos.zonal.degree_in_sign
                            natal_sign = natal_pos.zonal.sign_name
                            natal_degree = natal_pos.zonal.degree_in_sign

                            # Calculate houses for transiting and natal positions
                            transit_house = None
                            natal_house = None

                            # Extract house numbers and cusps as sorted list
                            house_items = [(k, v) for k, v in house_cusps.items() if k.startswith("house_")]
                            house_items.sort(key=lambda x: int(x[0].replace("house_", "")))

                            for i, (house_num, cusp) in enumerate(house_items):
                                # Get next house cusp (wrap around)
                                next_i = (i + 1) % len(house_items)
                                next_cusp = house_items[next_i][1]

                                # Use .longitude for ZonalPosition objects
                                cusp_lon = cusp.longitude if hasattr(cusp, 'longitude') else cusp
                                next_cusp_lon = next_cusp.longitude if hasattr(next_cusp, 'longitude') else next_cusp

                                # Check if position falls in this house (handle sign wrap-around)
                                if transit_sign == "Pisces" or (cusp_lon <= transiting_pos.longitude < next_cusp_lon):
                                    transit_house = int(house_num.replace("house_", ""))
                                if cusp_lon <= natal_pos.longitude < next_cusp_lon:
                                    natal_house = int(house_num.replace("house_", ""))

                            # Calculate peak orb window around exact time
                            peak_window_start = exact_time - timedelta(hours=24)
                            peak_window_end = exact_time + timedelta(hours=24)

                            transit_events.append({
                                "transiting_planet": transiting_pos.planet.name,
                                "natal_planet": natal_planet.name,
                                "aspect_type": aspect_name,
                                "orb_size": round(exact_orb, 2),
                                "significance_score": round(significance_score, 3),
                                "exact_timestamp": exact_time.isoformat(),
                                "transiting_sign": transit_sign,
                                "transiting_degree": round(transit_degree, 2),
                                "natal_sign": natal_sign,
                                "natal_degree": round(natal_degree, 2),
                                "transiting_house": transit_house,
                                "natal_house": natal_house,
                                # Peak orb window: exact moment + 1 degree range
                                "peak_orb_window": {
                                    "exact_moment": exact_time.isoformat(),
                                    "orb_range_degrees": round(exact_orb, 2),
                                    "within_1_degree_window": {
                                        "start": peak_window_start.isoformat(),
                                        "end": peak_window_end.isoformat()
                                    }
                                },
                            })
            
            current_date += hour_increment
        
        # Deduplicate events: keep only the highest-scoring event per planet pair + aspect type
        seen_events = set()
        unique_events = []
        for event in transit_events:
            key = (
                event["transiting_planet"],
                event["natal_planet"],
                event["aspect_type"]
            )
            if key not in seen_events:
                seen_events.add(key)
                unique_events.append(event)
        transit_events = unique_events
        
        # Apply grouping if requested
        grouped_events: dict[str, list[dict[str, Any]]] = {}
        
        if params.group_by:
            for event in transit_events:
                if params.group_by == 'house':
                    # Group by first house (transiting or natal)
                    key = str(event.get('transiting_house') or event.get('natal_house'))
                elif params.group_by == 'planet':
                    # Group by transiting planet
                    key = event.get('transiting_planet', '')
                elif params.group_by == 'theme':
                    # Group by aspect type
                    key = event.get('aspect_type', '')
                else:
                    key = ''
                
                if key:
                    if key not in grouped_events:
                        grouped_events[key] = []
                    grouped_events[key].append(event)
            
            # Keep only the highest-scoring event per group
            transit_events = []
            for group_key, group in grouped_events.items():
                if group:
                    # Sort within group and take highest
                    group.sort(key=lambda x: x['significance_score'], reverse=True)
                    transit_events.append(group[0])
        
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


async def handle_calculate_planet_aspect(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle calculate_planet_aspect tool call.
    
    Calculates the exact aspect between two planetary positions.
    """
    try:
        from astrology.core.aspects import (
            AspectType,
            calculate_aspect,
            get_exact_orb,
        )
        
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


async def handle_lunation_scan(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle lunation_scan tool call.

    Scans lunar phases and void-of-course periods over a date range.
    """
    from datetime import timezone

    try:
        from pydantic import BaseModel

        class LunationScanParams(BaseModel):
            start_date: str
            end_date: str
            include_void_of_course: bool = True
            natal_chart_id: str | None = None

        params = LunationScanParams(**arguments)

        # Parse dates
        start_dt = datetime.fromisoformat(params.start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(params.end_date.replace('Z', '+00:00'))

        # Convert to Julian Day for calculations
        from astrology.core.calendar import gregorian_to_julian_day
        jd_start = gregorian_to_julian_day(start_dt.year, start_dt.month, start_dt.day, start_dt.hour).jd
        jd_end = gregorian_to_julian_day(end_dt.year, end_dt.month, end_dt.day, end_dt.hour).jd

        # Scan for moon phases using real ephemeris calculations
        from astrology.core.ephemeris import scan_moon_phases, find_void_of_course_periods
        
        moon_phases = scan_moon_phases(jd_start, jd_end)
        
        # Scan for void-of-course periods
        void_of_course_periods = []
        if params.include_void_of_course:
            void_of_course_periods = find_void_of_course_periods(jd_start, jd_end)

        result = {
            "start_date": params.start_date,
            "end_date": params.end_date,
            "moon_phases": moon_phases,
            "void_of_course_periods": void_of_course_periods,
        }

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2),
        )]
    except Exception as e:
        logger.error(f"Error scanning lunation: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error scanning lunation: {str(e)}",
        )]


async def handle_get_houses(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle get_houses tool call."""
    return [TextContent(
        type="text",
        text="House calculation requires chart parameters. "
             "Use calculate_natal_chart instead.",
    )]
