"""Planetary ephemeris using Swiss Ephemeris."""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import NamedTuple

import swisseph as swe


class Planet(Enum):
    """Planets and important points in astrology."""
    SUN = auto()
    MOON = auto()
    MERCURY = auto()
    VENUS = auto()
    MARS = auto()
    JUPITER = auto()
    SATURN = auto()
    URANUS = auto()
    NEPTUNE = auto()
    PLUTO = auto()
    CHIRON = auto()
    LUNAR_NODE_MEAN = auto()  # Mean North Lunar Node
    LUNAR_NODE_TRUE = auto()  # True North Lunar Node
    LILITH_MEAN = auto()  # Mean Black Moon Lilith
    LILITH_TRUE = auto()  # True Black Moon Lilith
    ASCENDANT = auto()
    DESCENDANT = auto()
    MC = auto()  # Midpoint of Heaven (Medium Coeli)
    IC = auto()  # Immum Coeli


class ZonalPosition(NamedTuple):
    """Position in zodiac with sign and degree."""
    longitude: float  # Total degrees (0-360)
    sign_index: int   # 0-11 (Aries=0, Taurus=1, etc.)
    sign_name: str
    degree_in_sign: float  # Degrees within the sign (0-30)


class PlanetPosition(NamedTuple):
    """Planetary position data."""
    planet: Planet
    longitude: float  # Degrees in zodiac (0-360)
    latitude: float   # Degrees north/south of ecliptic
    distance: float   # Distance from Earth (typically in AU)
    retrograde: bool  # True if retrograde
    motion_speed: float  # Degrees per day

    @property
    def zonal(self) -> ZonalPosition:
        """Convert to zonal representation on demand."""
        return _convert_to_zonal(self.longitude)


# Swiss Ephemeris planet IDs
_PLANET_IDS = {
    Planet.SUN: swe.SUN,
    Planet.MOON: swe.MOON,
    Planet.MERCURY: swe.MERCURY,
    Planet.VENUS: swe.VENUS,
    Planet.MARS: swe.MARS,
    Planet.JUPITER: swe.JUPITER,
    Planet.SATURN: swe.SATURN,
    Planet.URANUS: swe.URANUS,
    Planet.NEPTUNE: swe.NEPTUNE,
    Planet.PLUTO: swe.PLUTO,
    Planet.CHIRON: swe.CHIRON,
    Planet.LUNAR_NODE_MEAN: swe.MEAN_NODE,
    Planet.LUNAR_NODE_TRUE: swe.TRUE_NODE,
    Planet.LILITH_MEAN: swe.MEAN_APOG,
    Planet.LILITH_TRUE: swe.OSCU_APOG,
}


# Zodiac names
ZODIAC_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


def _convert_to_zonal(longitude: float, zodiac_type: str = "tropical") -> ZonalPosition:
    """Convert longitude to zonal position (sign and degree).

    Args:
        longitude: Longitude in degrees (0-360)
        zodiac_type: "tropical" or "sidereal"

    Returns:
        ZonalPosition with sign and degree information
    """
    # Normalize longitude to 0-360
    longitude = longitude % 360

    # For tropical zodiac, start from 0° Aries (equinox)
    # For sidereal, we'd need to subtract ayanamsa
    if zodiac_type == "sidereal":
        # Apply Lahiri ayanamsa (approximately 24°)
        ayanamsa = 24.0
        longitude = (longitude - ayanamsa) % 360

    # Calculate sign and degree
    sign_index = int(longitude // 30)
    degree_in_sign = longitude % 30

    return ZonalPosition(
        longitude=longitude,
        sign_index=sign_index,
        sign_name=ZODIAC_NAMES[sign_index],
        degree_in_sign=degree_in_sign
    )


def _is_planet_retrograde(speed: float) -> bool:
    """Determine if a planet is retrograde based on its motion speed.

    Args:
        speed: Motion speed in degrees per day

    Returns:
        True if retrograde (negative speed)
    """
    return speed < 0


def init_swe(path: str | None = None) -> None:
    """Initialize Swiss Ephemeris.

    Args:
        path: Path to ephemeris files (optional)
              If None, Swiss Ephemeris will use default locations
    """
    if path:
        swe.set_ephe_path(path)
    else:
        # Try common ephemeris paths
        try_paths = [
            "/Users/amiekuttruff/ephe",
            "/usr/share/swisseph",
            "./ephe",
        ]
        for p in try_paths:
            try:
                swe.set_ephe_path(p)
                break
            except Exception:
                continue


def get_planet_position(planet: Planet, jd: float, zodiac_type: str = "tropical") -> PlanetPosition:
    """Get planetary position at a given Julian Day.

    Args:
        planet: The planet to calculate
        jd: Julian Day
        zodiac_type: "tropical" or "sidereal"

    Returns:
        PlanetPosition with longitude, latitude, distance, and motion info
    """
    if planet not in _PLANET_IDS:
        raise ValueError(f"Unsupported planet: {planet}")

    planet_id = _PLANET_IDS[planet]

    # Calculate position
    flag = swe.FLG_SWIEPH | swe.FLG_SPEED

    try:
        if planet in (Planet.ASCENDANT, Planet.DESCENDANT, Planet.MC, Planet.IC):
            # These require house calculation
            raise ValueError(f"Use calculate_houses() for {planet}")

        result, _ = swe.calc_ut(jd, planet_id, flag)

    except Exception as e:
        raise RuntimeError(f"Failed to calculate {planet}: {e}")

    # Parse result: [longitude, latitude, distance]
    longitude = result[0]
    latitude = result[1]
    distance = result[2]

    # Motion speed (degrees per day)
    speed = result[3] if len(result) > 3 else 0.0

    return PlanetPosition(
        planet=planet,
        longitude=longitude,  # Plain float (0-360)
        latitude=latitude,
        distance=distance,
        retrograde=_is_planet_retrograde(speed),
        motion_speed=speed
    )


def get_all_planets(jd: float, zodiac_type: str = "tropical") -> dict[Planet, PlanetPosition]:
    """Get positions of all planets at a given Julian Day.

    Args:
        jd: Julian Day
        zodiac_type: "tropical" or "sidereal"

    Returns:
        Dict mapping Planet to PlanetPosition
    """
    positions = {}

    for planet in [
        Planet.SUN, Planet.MOON,
        Planet.MERCURY, Planet.VENUS, Planet.MARS,
        Planet.JUPITER, Planet.SATURN,
        Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO
    ]:
        try:
            positions[planet] = get_planet_position(planet, jd, zodiac_type)
        except Exception as e:
            print(f"Warning: Could not calculate {planet}: {e}")

    return positions


def get_lunar_nodes(jd: float, use_true_node: bool = True) -> dict[str, PlanetPosition]:
    """Calculate lunar node positions.

    Args:
        jd: Julian Day
        use_true_node: If True, use true node; otherwise mean node

    Returns:
        Dict with 'north' and 'south' keys containing positions
    """
    node = Planet.LUNAR_NODE_TRUE if use_true_node else Planet.LUNAR_NODE_MEAN
    planet_id = _PLANET_IDS[node]

    flag = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flag)

    longitude = result[0]
    speed = result[3] if len(result) > 3 else 0.0

    position = PlanetPosition(
        planet=node,
        longitude=longitude,  # Plain float (0-360)
        latitude=result[1],
        distance=result[2],
        retrograde=_is_planet_retrograde(speed),
        motion_speed=speed
    )

    # South node is 180° opposite
    south_longitude = (longitude + 180) % 360

    return {
        "north": position,
        "south": PlanetPosition(
            planet=Planet.LUNAR_NODE_TRUE if not use_true_node else Planet.LUNAR_NODE_MEAN,
            longitude=south_longitude,  # Plain float (0-360)
            latitude=-position.latitude,
            distance=position.distance,
            retrograde=position.retrograde,
            motion_speed=position.motion_speed
        )
    }


def get_lilith_position(jd: float, use_true: bool = True) -> PlanetPosition:
    """Calculate Black Moon Lilith position.

    Args:
        jd: Julian Day
        use_true: If True, use true Lilith; otherwise mean

    Returns:
        PlanetPosition for Lilith
    """
    lilith = Planet.LILITH_TRUE if use_true else Planet.LILITH_MEAN
    planet_id = _PLANET_IDS[lilith]

    flag = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flag)

    return PlanetPosition(
        planet=lilith,
        longitude=result[0],  # Plain float (0-360)
        latitude=result[1],
        distance=result[2],
        retrograde=_is_planet_retrograde(result[3]),
        motion_speed=result[3]
    )


def calculate_houses(
    jd: float,
    latitude: float,
    longitude: float,
    house_system: str = "W"  # W = Whole Sign
) -> dict:
    """Calculate house cusps using Swiss Ephemeris.

    Args:
        jd: Julian Day
        latitude: Geographic latitude in degrees
        longitude: Geographic longitude in degrees
        house_system: Single letter for house system:
                     'W' = Whole Sign
                     'P' = Placidus
                     'E' = Equal House
                     'K' = Koch
                     'O' = Porphyry
                     'R' = Regiomontanus

    Returns:
        Dict with house positions and angles
    """
    flag = swe.FLG_SWIEPH

    # Calculate sidereal time
    t = (jd - 2451545.0) / 36525.0
    gst = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
    lst = (gst + longitude) % 360

    # Calculate houses
    try:
        cusps, ascmc = swe.houses(
            jd, latitude, longitude, house_system.encode()
        )
    except Exception as e:
        raise RuntimeError(f"Failed to calculate houses: {e}")

    # Parse results
    houses = {}
    for i, cusp in enumerate(cusps):
        house_num = i + 1
        houses[f"house_{house_num}"] = _convert_to_zonal(cusp)

    # Ascendant, MC, etc.
    houses["ascendant"] = _convert_to_zonal(ascmc[0])
    houses["mc"] = _convert_to_zonal(ascmc[1])
    houses["descendant"] = _convert_to_zonal(ascmc[2])
    houses["ic"] = _convert_to_zonal(ascmc[3])

    return houses


def calculate_ayanamsa(jd: float) -> float:
    """Calculate the ayanamsa (precession of equinoxes).

    Args:
        jd: Julian Day

    Returns:
        Ayanamsa in degrees (the difference between tropical and sidereal)
    """
    # Lahiri ayanamsa is commonly used
    # This is an approximation
    t = (jd - 2451545.0) / 36525.0
    ayanamsa = 24.0 + 0.01397 * t - 0.000002 * t**2
    return ayanamsa
