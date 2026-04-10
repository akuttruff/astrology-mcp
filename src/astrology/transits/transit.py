"""Transit calculations for astrology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple

from ..core.aspects import (
    Aspect,
    AspectType,
    DEFAULT_ORBS,
    calculate_aspect,
    calculate_planet_aspect,
    get_major_aspects,
)
from ..core.calendar import JulianDay, gregorian_to_julian_day
from ..core.ephemeris import (
    Planet,
    PlanetPosition,
    get_all_planets,
)
from ..charts.chart import NatalChart


class TransitEvent(NamedTuple):
    """A transit event between a transiting planet and natal planet/point."""
    planet: Planet
    natal_position: float  # Natal longitude in degrees
    transit_position: float  # Transiting longitude in degrees
    aspect_type: AspectType
    orb: float  # Distance from exact aspect


class TransitConfiguration(NamedTuple):
    """A transit configuration with multiple aspects."""
    date: datetime
    planet: Planet
    transiting_position: float
    natal_positions: dict[Planet, float]  # Natal positions being transited
    aspects: list[TransitEvent]


@dataclass
class TransitReport:
    """Complete transit report."""
    date: datetime
    transiting_planets: dict[Planet, PlanetPosition]
    natal_chart: NatalChart
    transits: list[TransitEvent]


def calculate_single_transit(
    planet: Planet,
    natal_chart: NatalChart,
    transiting_jd: float,
) -> list[TransitEvent]:
    """Calculate transits for a single planet.

    Args:
        planet: The transiting planet
        natal_chart: The natal chart to check against
        transiting_jd: Julian Day for the transit date

    Returns:
        List of TransitEvent objects
    """
    from ..core.ephemeris import get_planet_position

    transiting_pos = get_planet_position(planet, transiting_jd)

    events = []
    
    # Build natal positions dict with full position objects
    natal_positions: dict[Planet, PlanetPosition] = {}
    
    # Add planetary positions
    for planet_obj, pos in natal_chart.planets.items():
        natal_positions[planet_obj] = pos
    
    # Add angles
    if natal_chart.ascendant:
        natal_positions[Planet.ASCENDANT] = PlanetPosition(
            planet=Planet.ASCENDANT,
            longitude=natal_chart.ascendant.longitude,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=0.0,
        )
    if natal_chart.midheaven:
        natal_positions[Planet.MC] = PlanetPosition(
            planet=Planet.MC,
            longitude=natal_chart.midheaven.longitude,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=0.0,
        )

    # Check aspects to each natal planet/point
    for natal_planet, natal_pos in natal_positions.items():
        aspect = calculate_planet_aspect(
            planet,
            natal_planet,
            transiting_pos,
            natal_pos,
        )
        if aspect:
            event = TransitEvent(
                planet=planet,
                natal_position=natal_pos.longitude,  # Already a float (0-360 degrees)
                transit_position=transiting_pos.longitude,  # Already a float (0-360 degrees)
                aspect_type=aspect.type,
                orb=aspect.orb,
            )
            events.append(event)

    return events


def get_current_transits(
    natal_chart: NatalChart,
    current_datetime: datetime | None = None,
) -> TransitReport:
    """Get all current transits.

    Args:
        natal_chart: The natal chart
        current_datetime: Current date/time (defaults to now)

    Returns:
        TransitReport with all transits
    """
    if current_datetime is None:
        current_datetime = datetime.utcnow()

    # Get current planetary positions
    jd = gregorian_to_julian_day(
        current_datetime.year,
        current_datetime.month,
        current_datetime.day,
        current_datetime.hour
    )

    transiting_planets = get_all_planets(jd.jd)

    # Calculate transits for all planets
    all_transits = []
    major_planets = [
        Planet.SUN, Planet.MOON,
        Planet.MERCURY, Planet.VENUS, Planet.MARS,
        Planet.JUPITER, Planet.SATURN,
        Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO
    ]

    for planet in major_planets:
        if planet in transiting_planets:
            events = calculate_single_transit(planet, natal_chart, jd.jd)
            all_transits.extend(events)

    # Sort by orb (most significant first)
    all_transits.sort(key=lambda e: e.orb)

    return TransitReport(
        date=current_datetime,
        transiting_planets=transiting_planets,
        natal_chart=natal_chart,
        transits=all_transits,
    )


def find_major_transit_dates(
    transit_planet: Planet,
    natal_chart: NatalChart,
    start_date: datetime,
    end_date: datetime,
    aspect_type: AspectType | None = None,
) -> list[TransitConfiguration]:
    """Find dates when a planet makes major aspects.

    Args:
        transit_planet: The transiting planet
        natal_chart: The natal chart
        start_date: Start date for search
        end_date: End date for search
        aspect_type: Specific aspect to find (None = all)

    Returns:
        List of TransitConfiguration objects
    """
    # Sample dates between start and end
    days = (end_date - start_date).days
    sample_interval = 1  # Check daily

    results = []

    for day in range(0, days + 1, sample_interval):
        check_date = start_date + timedelta(days=day)
        jd = gregorian_to_julian_day(check_date.year, check_date.month, check_date.day)

        transiting_pos = get_all_planets(jd.jd)
        if transit_planet not in transiting_pos:
            continue

        transiting_planet_pos = transiting_pos[transit_planet]

        # Check aspects to natal planets
        natal_positions = {
            planet: pos.longitude  # Already a float (0-360 degrees)
            for planet, pos in natal_chart.planets.items()
        }

        aspects = []
        for natal_planet, natal_lon in natal_positions.items():
            aspect = calculate_aspect(
                transiting_planet_pos.longitude.longitude,
                natal_lon
            )
            aspect_type_found, exact_angle = aspect

            # Calculate orb
            diff = abs((transiting_planet_pos.longitude.longitude - natal_lon) % 360)
            if diff > 180:
                diff = 360 - diff

            orb = abs(diff - exact_angle)
            max_orb = DEFAULT_ORBS.get(aspect_type_found, 8.0)

            if orb <= max_orb:
                if aspect_type is None or aspect_type == aspect_type_found:
                    aspects.append(TransitEvent(
                        planet=transit_planet,
                        natal_position=natal_lon,
                        transit_position=transiting_planet_pos.longitude.longitude,
                        aspect_type=aspect_type_found,
                        orb=orb,
                    ))

        if aspects:
            results.append(TransitConfiguration(
                date=check_date,
                planet=transit_planet,
                transiting_position=transiting_planet_pos.longitude.longitude,
                natal_positions=natal_positions,
                aspects=aspects,
            ))

    return results


def get_transit_summary(transits: list[TransitEvent], limit: int = 10) -> str:
    """Get a human-readable summary of transits.

    Args:
        transits: List of TransitEvent objects
        limit: Maximum number of events to show

    Returns:
        Formatted string summary
    """
    if not transits:
        return "No significant transits currently active."

    lines = ["Current Transits:"]
    lines.append("=" * 50)

    for event in transits[:limit]:
        aspect_name = event.aspect_type.name.title()
        lines.append(
            f"{event.planet.name} transiting {aspect_name} "
            f"natal position (orb: {event.orb:.1f}°)"
        )

    if len(transits) > limit:
        lines.append(f"... and {len(transits) - limit} more")

    return "\n".join(lines)
