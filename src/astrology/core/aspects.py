"""Planetary aspect calculations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

from .ephemeris import Planet, PlanetPosition


class AspectType(Enum):
    """Types of astrological aspects."""
    CONJUNCTION = auto()      # 0°
    ORIENTATION = auto()     # 45° (Octile)
    SEPTILE = auto()         # 51.43°
    SQUARE = auto()          # 90°
    TRINE = auto()           # 120°
    SEXTILE = auto()         # 60°
    OPPOSITION = auto()      # 180°
    QUINCUNX = auto()        # 150°
    SEMI_SEXTILE = auto()    # 30°
    SEMI_SQUARE = auto()     # 45°
    SESQUI_SQUARE = auto()   # 135°


@dataclass
class Aspect:
    """An aspect between two planets."""
    type: AspectType
    planet1: Planet
    planet2: Planet
    angle: float          # Exact angle in degrees
    orb: float            # How far from exact aspect (degrees)
    distance: float       # Actual angular separation (degrees)
    is_applying: bool     # True if planets are moving toward exact aspect
    is_separating: bool   # True if planets are moving away from exact aspect


# Default orbs for major aspects
DEFAULT_ORBS = {
    AspectType.CONJUNCTION: 8.0,
    AspectType.ORIENTATION: 3.0,
    AspectType.SEPTILE: 2.0,
    AspectType.SQUARE: 5.0,
    AspectType.TRINE: 5.0,
    AspectType.SEXTILE: 3.0,
    AspectType.OPPOSITION: 8.0,
    AspectType.QUINCUNX: 2.0,
    AspectType.SEMI_SEXTILE: 1.5,
    AspectType.SEMI_SQUARE: 2.0,
    AspectType.SESQUI_SQUARE: 2.0,
}

# Aspect angles - sorted by frequency for early exit optimization
ASPECT_ANGLES = {
    AspectType.CONJUNCTION: 0.0,
    AspectType.OPPOSITION: 180.0,
    AspectType.SQUARE: 90.0,
    AspectType.TRINE: 120.0,
    AspectType.SEXTILE: 60.0,
    AspectType.ORIENTATION: 45.0,
    AspectType.SEMI_SQUARE: 45.0,
    AspectType.SEPTILE: 51.4285714286,
    AspectType.SEMI_SEXTILE: 30.0,
    AspectType.QUINCUNX: 150.0,
    AspectType.SESQUI_SQUARE: 135.0,
}

# Pre-computed angles list for faster iteration
_ASPECT_ANGLE_LIST = list(ASPECT_ANGLES.items())

# Aspect names for display
ASPECT_NAMES = {
    AspectType.CONJUNCTION: "Conjunction",
    AspectType.ORIENTATION: "Octile",
    AspectType.SEPTILE: "Septile",
    AspectType.SQUARE: "Square",
    AspectType.TRINE: "Trine",
    AspectType.SEXTILE: "Sextile",
    AspectType.OPPOSITION: "Opposition",
    AspectType.QUINCUNX: "Quincunx",
    AspectType.SEMI_SEXTILE: "Semi-Sextile",
    AspectType.SEMI_SQUARE: "Semi-Square",
    AspectType.SESQUI_SQUARE: "Sesqui-Square",
}


def calculate_aspect(
    planet1_lon: float,
    planet2_lon: float,
) -> tuple[AspectType, float]:
    """Calculate the aspect type and angle between two planets.

    Args:
        planet1_lon: Planet 1's longitude in degrees (0-360)
        planet2_lon: Planet 2's longitude in degrees (0-360)

    Returns:
        Tuple of (AspectType, exact_angle)
    """
    # Normalize longitudes
    lon1 = planet1_lon % 360
    lon2 = planet2_lon % 360

    # Calculate angular separation (shortest arc)
    diff = abs(lon2 - lon1)
    if diff > 180:
        diff = 360 - diff

    # Find the closest aspect using pre-computed list
    best_aspect = AspectType.CONJUNCTION
    best_angle = 0.0
    min_diff = diff

    for aspect_type, angle in _ASPECT_ANGLE_LIST:
        # Early exit: perfect match
        if diff == angle:
            return aspect_type, angle
        
        # Check both direct and orb-like cases
        for base_angle in (angle, angle - 360):
            diff_from_aspect = abs(diff - base_angle)
            if diff_from_aspect < min_diff:
                min_diff = diff_from_aspect
                best_aspect = aspect_type
                best_angle = angle

    return best_aspect, best_angle


def get_exact_orb(aspect_type: AspectType, custom_orbs: dict | None = None) -> float:
    """Get the maximum orb for an aspect type.

    Args:
        aspect_type: The aspect to check
        custom_orbs: Optional dict of custom orbs

    Returns:
        Orb in degrees
    """
    if custom_orbs and aspect_type in custom_orbs:
        return custom_orbs[aspect_type]
    return DEFAULT_ORBS.get(aspect_type, 8.0)


def calculate_planet_aspect(
    planet1: Planet,
    planet2: Planet,
    position1: PlanetPosition,
    position2: PlanetPosition,
    custom_orbs: dict | None = None,
) -> Aspect | None:
    """Calculate aspect between two planets with position data.

    Args:
        planet1: First planet
        planet2: Second planet
        position1: Position data for first planet
        position2: Position data for second planet
        custom_orbs: Optional dict of custom orbs

    Returns:
        Aspect if within orb, or None
    """
    # Extract longitude - PlanetPosition.longitude is always a plain float (0-360)
    lon1 = position1.longitude
    lon2 = position2.longitude

    # Get exact aspect angle and type
    aspect_type, exact_angle = calculate_aspect(lon1, lon2)

    # Calculate angular separation
    diff = abs((lon2 - lon1) % 360)
    if diff > 180:
        diff = 360 - diff

    # Calculate orb (how far from exact aspect)
    orb = abs(diff - exact_angle)

    # Check if within orb
    max_orb = get_exact_orb(aspect_type, custom_orbs)
    if orb > max_orb:
        return None

    # Determine if applying or separating
    # Use motion_speed if available, otherwise default to 0 (unknown motion)
    speed1 = getattr(position1, 'motion_speed', 0.0) or 0.0
    speed2 = getattr(position2, 'motion_speed', 0.0) or 0.0

    is_applying = False
    is_separating = False

    # Only determine applying/separating if both speeds are known (non-zero)
    if speed1 != 0.0 or speed2 != 0.0:
        # Determine relative motion
        if lon1 < lon2:
            # Planet 1 is behind planet 2
            if speed1 > speed2:
                # Planet 1 catching up (applying)
                is_applying = True
            else:
                # Planet 2 pulling away (separating)
                is_separating = True
        else:
            # Planet 2 is behind planet 1
            if speed2 > speed1:
                # Planet 2 catching up (applying)
                is_applying = True
            else:
                # Planet 1 pulling away (separating)
                is_separating = True
    else:
        # If speeds are unknown, mark as applying if orb is small (within 5°)
        # This provides a reasonable default for historical/future dates
        if orb < 5.0:
            is_applying = True

    return Aspect(
        type=aspect_type,
        planet1=planet1,
        planet2=planet2,
        angle=diff,
        orb=orb,
        distance=diff,
        is_applying=is_applying if not (is_applying and is_separating) else False,
        is_separating=is_separating if not (is_applying and is_separating) else False,
    )


def get_all_aspects(
    planets: dict[Planet, PlanetPosition],
    custom_orbs: dict | None = None,
) -> list[Aspect]:
    """Calculate all aspects between planets.

    Args:
        planets: Dict of planet to position
        custom_orbs: Optional dict of custom orbs

    Returns:
        List of Aspect objects (excluding conjunctions with self)
    """
    aspects = []
    planet_list = list(planets.items())

    for i, (p1, pos1) in enumerate(planet_list):
        for p2, pos2 in planet_list[i + 1:]:
            aspect = calculate_planet_aspect(p1, p2, pos1, pos2, custom_orbs)
            if aspect:
                aspects.append(aspect)

    # Sort by orb (tightest first)
    aspects.sort(key=lambda a: a.orb)

    return aspects


def get_major_aspects(
    planets: dict[Planet, PlanetPosition],
) -> list[Aspect]:
    """Get only major aspects (conjunction, square, opposition, trine, sextile).

    Args:
        planets: Dict of planet to position

    Returns:
        List of major Aspect objects
    """
    major_types = {
        AspectType.CONJUNCTION,
        AspectType.SQUARE,
        AspectType.OPPOSITION,
        AspectType.TRINE,
        AspectType.SEXTILE,
    }

    all_aspects = get_all_aspects(planets)
    return [a for a in all_aspects if a.type in major_types]


def get_aspect_string(aspect: Aspect) -> str:
    """Get a human-readable string for an aspect."""
    name = ASPECT_NAMES.get(aspect.type, str(aspect.type))
    applying_str = "applying" if aspect.is_applying else "separating"
    return f"{name} ({aspect.planet1.name} - {aspect.planet2.name}) {aspect.orb:.1f}° {applying_str}"
