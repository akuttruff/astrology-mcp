"""Solar arc progressions for astrology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from ..core.calendar import JulianDay, gregorian_to_julian_day
from ..core.ephemeris import (
    Planet,
    PlanetPosition,
    ZonalPosition,
    get_planet_position,
)
from ..charts.chart import NatalChart, calculate_natal_chart


class ProgressedPosition(NamedTuple):
    """Progressed position for a planet or point."""
    planet: Planet
    natal_position: float  # Original longitude
    sun_arc: float          # Arc Sun has traveled since birth
    progressed_longitude: float  # New longitude after progressions


@dataclass
class SolarArcProgressedChart:
    """A solar arc progressed chart."""
    natal_chart: NatalChart
    progression_date: datetime
    sun_arc: float  # Degrees Sun has moved since birth
    progressed_planets: dict[Planet, ProgressedPosition] = None  # type: ignore
    progressed_ascendant: float | None = None
    progressed_mc: float | None = None

    def __post_init__(self):
        if self.progressed_planets is None:
            self.progressed_planets = {}


def calculate_solar_arc(natal_chart: NatalChart, current_date: datetime) -> float:
    """Calculate the solar arc (how far Sun has moved since birth).

    Args:
        natal_chart: The natal chart
        current_date: Date to calculate progression to

    Returns:
        Solar arc in degrees
    """
    # Get Sun's position at birth and current date
    birth_jd = natal_chart.chart_time.julian_day.jd

    birth_pos = get_planet_position(Planet.SUN, birth_jd)
    current_jd = gregorian_to_julian_day(current_date.year, current_date.month, current_date.day)
    current_pos = get_planet_position(Planet.SUN, current_jd.jd)

    # Calculate arc (difference in longitude)
    sun_arc = current_pos.longitude - birth_pos.longitude

    # Normalize to 0-360
    sun_arc = sun_arc % 360

    return sun_arc


def calculate_solar_arc_progressed_chart(
    natal_chart: NatalChart,
    current_date: datetime,
) -> SolarArcProgressedChart:
    """Calculate a complete solar arc progressed chart.

    Args:
        natal_chart: The natal chart
        current_date: Date to calculate progression to

    Returns:
        SolarArcProgressedChart with all progressed positions
    """
    # Calculate solar arc
    sun_arc = calculate_solar_arc(natal_chart, current_date)

    # Progress each planet
    progressed_planets = {}
    for planet, position in natal_chart.planets.items():
        # Add solar arc to natal position
        progressed_lon = (position.longitude + sun_arc) % 360

        # Create progressed position
        progressed_planets[planet] = ProgressedPosition(
            planet=planet,
            natal_position=position.longitude,
            sun_arc=sun_arc,
            progressed_longitude=progressed_lon,
        )

    # Progress angles (Ascendant, MC)
    if natal_chart.ascendant:
        progressed_asc = (natal_chart.ascendant.longitude + sun_arc) % 360
    else:
        progressed_asc = None

    if natal_chart.midheaven:
        progressed_mc = (natal_chart.midheaven.longitude + sun_arc) % 360
    else:
        progressed_mc = None

    chart = SolarArcProgressedChart(
        natal_chart=natal_chart,
        progression_date=current_date,
        sun_arc=sun_arc,
        progressed_planets=progressed_planets,
        progressed_ascendant=progressed_asc,
        progressed_mc=progressed_mc,
    )

    return chart


def progress_planet_position(
    natal_longitude: float,
    sun_arc: float,
) -> float:
    """Progress a single planet's longitude.

    Args:
        natal_longitude: Natal longitude in degrees (0-360)
        sun_arc: Solar arc to add

    Returns:
        Progressed longitude in degrees (0-360)
    """
    return (natal_longitude + sun_arc) % 360


def get_progression_aspect(
    natal_chart: NatalChart,
    progressed_chart: SolarArcProgressedChart,
) -> list:
    """Get aspects between natal and progressed positions.

    Args:
        natal_chart: The natal chart
        progressed_chart: The solar arc progressed chart

    Returns:
        List of aspects between natal and progressed planets
    """
    from ..core.aspects import calculate_aspect, AspectType

    aspects = []

    for planet, progressed_pos in progressed_chart.progressed_planets.items():
        natal_pos = natal_chart.planets.get(planet)
        if not natal_pos:
            continue

        # Calculate aspect between natal and progressed
        aspect_type, exact_angle = calculate_aspect(
            natal_pos.longitude,
            progressed_pos.progressed_longitude
        )

        # Calculate orb
        diff = abs((progressed_pos.progressed_longitude - natal_pos.longitude) % 360)
        if diff > 180:
            diff = 360 - diff

        orb = abs(diff - exact_angle)

        # Only include significant aspects
        if orb <= 3.0:
            aspects.append({
                "planet": planet,
                "aspect_type": aspect_type,
                "orb": orb,
                "natal_position": natal_pos.longitude,
                "progressed_position": progressed_pos.progressed_longitude,
            })

    return aspects


def calculate_progression_date(
    natal_datetime: datetime,
    current_datetime: datetime,
) -> tuple[float, float]:
    """Calculate progression date metrics.

    Args:
        natal_datetime: Birth date/time
        current_datetime: Current date/time

    Returns:
        Tuple of (days_since_birth, years_since_birth)
    """
    delta = current_datetime - natal_datetime
    days = delta.days + delta.seconds / 86400
    years = days / 365.25

    return days, years


def get_progression_summary(
    progressed_chart: SolarArcProgressedChart,
) -> str:
    """Get a human-readable summary of the progressed chart.

    Args:
        progressed_chart: The solar arc progressed chart

    Returns:
        Formatted string summary
    """
    lines = [
        "Solar Arc Progressed Chart",
        "=" * 40,
        f"Progression Date: {progressed_chart.progression_date.strftime('%Y-%m-%d')}",
        f"Sun Arc: {progressed_chart.sun_arc:.2f}°",
        "",
        "Progressed Planets:",
    ]

    for planet, pos in progressed_chart.progressed_planets.items():
        # Convert longitude to sign and degree
        sign_index = int(pos.progressed_longitude // 30)
        sign_name = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ][sign_index]
        degree = pos.progressed_longitude % 30

        lines.append(f"  {planet.name}: {sign_name} {degree:.1f}°")

    if progressed_chart.progressed_ascendant:
        sign_index = int(progressed_chart.progressed_ascendant // 30)
        sign_name = ["Aries", "Taurus", "Gemini", "Cancer",
                     "Leo", "Virgo", "Libra", "Scorpio",
                     "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sign_index]
        degree = progressed_chart.progressed_ascendant % 30
        lines.append(f"  Ascendant: {sign_name} {degree:.1f}°")

    if progressed_chart.progressed_mc:
        sign_index = int(progressed_chart.progressed_mc // 30)
        sign_name = ["Aries", "Taurus", "Gemini", "Cancer",
                     "Leo", "Virgo", "Libra", "Scorpio",
                     "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sign_index]
        degree = progressed_chart.progressed_mc % 30
        lines.append(f"  MC: {sign_name} {degree:.1f}°")

    return "\n".join(lines)
