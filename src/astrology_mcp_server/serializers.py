"""Data serialization functions for Astrology MCP Server.

This module handles converting between NatalChart objects and dictionaries
for caching and transmission.
"""

from __future__ import annotations

from typing import Any

from astrology.charts.chart import NatalChart
from astrology.core.ephemeris import ZonalPosition, ZODIAC_NAMES


def _serialize_chart(chart: NatalChart) -> dict[str, Any]:
    """Convert NatalChart to serializable dictionary.
    
    Args:
        chart: The NatalChart object to serialize
    
    Returns:
        Dictionary representation suitable for JSON serialization
    """
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


def _build_chart_preview(chart: NatalChart) -> dict[str, Any]:
    """Build a preview dictionary with key highlights for quick decisions.
    
    Args:
        chart: The NatalChart object
    
    Returns:
        Dictionary with sun, moon, and ascendant information
    """
    preview = {}
    
    # Get planetary positions for preview
    for planet, position in chart.planets.items():
        if planet.name in ["SUN", "MOON"]:
            preview[planet.name.lower()] = {
                "sign": position.zonal.sign_name,
                "degree": round(position.zonal.degree_in_sign, 2),
            }
    
    # Get ascendant
    if chart.ascendant:
        preview["ascendant"] = {
            "sign": chart.ascendant.sign_name,
            "degree": round(chart.ascendant.degree_in_sign, 2),
        }
    
    return preview


def _serialize_zonal(zonal: ZonalPosition | None) -> dict | None:
    """Serialize a ZonalPosition to a dictionary.
    
    Args:
        zonal: The ZonalPosition object to serialize
    
    Returns:
        Dictionary representation or None if input is None
    """
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
