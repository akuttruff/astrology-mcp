"""Natal chart calculation module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple

from ..core.calendar import Location, ChartTime, create_chart_time
from ..core.ephemeris import (
    Planet,
    PlanetPosition,
    ZonalPosition,
    get_all_planets,
    calculate_houses,
)


class House(NamedTuple):
    """Represents a house in the chart."""
    number: int
    cusp: ZonalPosition  # The zodiac position of the house cusp
    planet_in_house: Planet | None = None  # Any planet within this house


@dataclass
class NatalChart:
    """Complete natal chart data."""
    # Chart metadata
    birth_datetime: datetime
    location: Location

    # Time data
    chart_time: ChartTime

    # Planetary positions
    planets: dict[Planet, PlanetPosition] = field(default_factory=dict)

    # House cusps
    houses: dict = field(default_factory=dict)

    # House placements
    house_positions: dict[Planet, int] = field(default_factory=dict)

    # Angles
    ascendant: ZonalPosition | None = None
    descendant: ZonalPosition | None = None
    midheaven: ZonalPosition | None = None  # MC
    ic: ZonalPosition | None = None  # IC

    # Planetary nodes and points
    lunar_north_node: PlanetPosition | None = None
    lunar_south_node: PlanetPosition | None = None
    Lilith: PlanetPosition | None = None

    def get_planet_house(self, planet: Planet) -> int | None:
        """Get the house number for a given planet."""
        return self.house_positions.get(planet)

    def get_planet_sign(self, planet: Planet) -> str:
        """Get the zodiac sign for a given planet."""
        if planet in self.planets:
            return self.planets[planet].zonal.sign_name
        if planet == Planet.ASCENDANT and self.ascendant:
            return self.ascendant.sign_name
        if planet == Planet.MC and self.midheaven:
            return self.midheaven.sign_name
        return "Unknown"

    def get_planet_degree(self, planet: Planet) -> float:
        """Get the degree within sign for a given planet."""
        if planet in self.planets:
            return self.planets[planet].zonal.degree_in_sign
        if planet == Planet.ASCENDANT and self.ascendant:
            return self.ascendant.degree_in_sign
        if planet == Planet.MC and self.midheaven:
            return self.midheaven.degree_in_sign
        return 0.0

    def get_planet_longitude(self, planet: Planet) -> float:
        """Get the total longitude for a given planet."""
        if planet in self.planets:
            return self.planets[planet].longitude
        if planet == Planet.ASCENDANT and self.ascendant:
            return self.ascendant.longitude
        if planet == Planet.MC and self.midheaven:
            return self.midheaven.longitude
        return 0.0

    def is_planet_retrograde(self, planet: Planet) -> bool:
        """Check if a planet is retrograde."""
        return self.planets.get(planet, PlanetPosition).retrograde


def calculate_natal_chart(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
    zodiac_type: str = "tropical",
    house_system: str = "W",  # W = Whole Sign
) -> NatalChart:
    """Calculate a complete natal chart.

    Args:
        birth_datetime: Birth date and time
        latitude: Geographic latitude in degrees (positive north)
        longitude: Geographic longitude in degrees (positive east)
        elevation: Elevation above sea level (meters)
        zodiac_type: "tropical" or "sidereal"
        house_system: House system code:
                     'W' = Whole Sign (default)
                     'P' = Placidus
                     'E' = Equal House
                     'K' = Koch
                     'O' = Porphyry

    Returns:
        NatalChart with all calculated data
    """
    location = Location(latitude=latitude, longitude=longitude, elevation=elevation)

    # Create chart time
    chart_time = create_chart_time(birth_datetime, location)

    # Get planetary positions
    planets = get_all_planets(chart_time.julian_day.jd, zodiac_type)

    # Calculate houses
    houses_data = calculate_houses(
        chart_time.julian_day.jd,
        latitude,
        longitude,
        house_system
    )

    # Extract angles
    ascendant = houses_data.get("ascendant")
    mc = houses_data.get("mc")
    descendant = houses_data.get("descendant")
    ic = houses_data.get("ic")

    # Calculate lunar nodes
    from ..core.ephemeris import get_lunar_nodes, get_lilith_position

    lunar_nodes = get_lunar_nodes(chart_time.julian_day.jd, use_true_node=True)
    Lilith = get_lilith_position(chart_time.julian_day.jd, use_true=True)

    # Determine which house each planet is in
    house_positions = {}
    for planet, position in planets.items():
        # PlanetPosition.longitude is now a plain float (0-360)
        planet_lon = position.longitude
        planet_house = _find_planet_house(planet_lon, houses_data)
        house_positions[planet] = planet_house

    return NatalChart(
        birth_datetime=birth_datetime,
        location=location,
        chart_time=chart_time,
        planets=planets,
        houses=houses_data,
        house_positions=house_positions,
        ascendant=ascendant,
        midheaven=mc,
        descendant=descendant,
        ic=ic,
        lunar_north_node=lunar_nodes.get("north"),
        lunar_south_node=lunar_nodes.get("south"),
        Lilith=Lilith,
    )


def _find_planet_house(planet_longitude: float, houses_data: dict) -> int:
    """Find which house a planet is in based on its longitude.

    Args:
        planet_longitude: Planet's longitude in degrees (0-360)
        houses_data: Dict with house cusp positions

    Returns:
        House number (1-12)
    """
    # Get the Ascendant to determine the 1st house sign
    ascendant = houses_data.get("ascendant")
    if not ascendant:
        # Fallback: use the first house cusp
        cusp = houses_data.get("house_1")
        if not cusp:
            return 1
        asc_sign_index = cusp.sign_index
    else:
        asc_sign_index = ascendant.sign_index

    # Helper function to extract longitude from house cusp (handles both ZonalPosition and dict)
    def get_longitude(cusp) -> float:
        if hasattr(cusp, "longitude"):
            return cusp.longitude
        elif isinstance(cusp, dict) and "longitude" in cusp:
            return float(cusp["longitude"])
        elif isinstance(cusp, (int, float)):
            return float(cusp)
        else:
            return 0.0

    # Check if this is Whole Sign house system (all house cusps at sign boundaries)
    # For Whole Sign, all house_1 through house_12 should be at 0° of their signs
    is_whole_sign = True
    for i in range(1, 13):
        cusp = houses_data.get(f"house_{i}")
        if cusp:
            lon = get_longitude(cusp)
            # Check if cusp is at 0° of a sign (within small tolerance)
            if abs(lon - int(lon // 30) * 30) > 0.01:
                is_whole_sign = False
                break

    if is_whole_sign:
        # For Whole Sign houses, House 1 starts at 0° of the Ascendant's sign
        # Calculate which house a planet is in based on its longitude relative to ASC sign
        planet_sign_index = int(planet_longitude // 30)

        # Calculate house number (1-12) based on sign offset from ASC
        house_number = ((planet_sign_index - asc_sign_index) % 12) + 1
    else:
        # For non-Whole Sign systems, compare against actual house cusps
        # Get all house cusps sorted by longitude
        house_cusps = []
        for i in range(1, 13):
            cusp = houses_data.get(f"house_{i}")
            if cusp:
                house_cusps.append((get_longitude(cusp), i))

        # Sort by longitude
        house_cusps.sort(key=lambda x: x[0])

        # Find which house the planet falls in
        for i, (cusp_lon, house_num) in enumerate(house_cusps):
            next_cusp_lon = house_cusps[(i + 1) % len(house_cusps)][0]

            if cusp_lon < next_cusp_lon:
                # Normal case: cusp to next cusp
                if cusp_lon <= planet_longitude < next_cusp_lon:
                    return house_num
            else:
                # Wraparound case (e.g., cusp at 350°, next at 20°)
                if planet_longitude >= cusp_lon or planet_longitude < next_cusp_lon:
                    return house_num

        # Fallback: if we didn't find a match, return 1
        return 1

    return house_number


def get_planet_in_sign(chart: NatalChart, sign_name: str) -> list[Planet]:
    """Get all planets in a specific zodiac sign.

    Args:
        chart: NatalChart to search
        sign_name: Name of zodiac sign (e.g., "Aries", "Leo")

    Returns:
        List of planets in that sign
    """
    matching = []
    for planet, position in chart.planets.items():
        # Use zonal property to access sign_name
        if position.zonal.sign_name == sign_name:
            matching.append(planet)
    return matching


def get_planet_in_house(chart: NatalChart, house_number: int) -> list[Planet]:
    """Get all planets in a specific house.

    Args:
        chart: NatalChart to search
        house_number: House number (1-12)

    Returns:
        List of planets in that house
    """
    matching = []
    for planet, house_num in chart.house_positions.items():
        if house_num == house_number:
            matching.append(planet)
    return matching


def get_planet_aspect_angles(chart: NatalChart) -> dict[Planet, float]:
    """Get the angle from each planet to the Ascendant.

    Args:
        chart: NatalChart

    Returns:
        Dict mapping planets to their angle from Ascendant (0-360)
    """
    if not chart.ascendant:
        return {}

    asc_lon = chart.ascendant.longitude
    angles = {}
    for planet, position in chart.planets.items():
        # PlanetPosition.longitude is now a plain float (0-360)
        planet_lon = position.longitude
        angle = (planet_lon - asc_lon) % 360
        angles[planet] = angle
    return angles


def get_planet_transit_house(
    chart: NatalChart,
    transit_longitude: float,
) -> int:
    """Calculate which house a transiting planet falls in.

    Args:
        chart: NatalChart with house cusps
        transit_longitude: Transiting planet's longitude (0-360)

    Returns:
        House number (1-12)
    """
    if not chart.ascendant:
        return 1

    # Helper function to extract longitude from house cusp (handles both ZonalPosition and dict)
    def get_longitude(cusp) -> float:
        if hasattr(cusp, "longitude"):
            return cusp.longitude
        elif isinstance(cusp, dict) and "longitude" in cusp:
            return float(cusp["longitude"])
        elif isinstance(cusp, (int, float)):
            return float(cusp)
        else:
            return 0.0

    # Check if this is Whole Sign house system
    asc_sign_index = int(chart.ascendant.longitude // 30)
    
    # Check if all house cusps are at sign boundaries (Whole Sign)
    is_whole_sign = True
    for house_num in range(1, 13):
        cusp = chart.houses.get(f"house_{house_num}")
        if cusp:
            lon = get_longitude(cusp)
            # Check if cusp is at 0° of a sign (within small tolerance)
            if abs(lon - int(lon // 30) * 30) > 0.01:
                is_whole_sign = False
                break

    if is_whole_sign:
        # For Whole Sign houses, House 1 starts at 0° of the Ascendant's sign
        planet_sign_index = int(transit_longitude // 30)

        # Calculate house number based on sign offset from ASC's sign
        house_number = ((planet_sign_index - asc_sign_index) % 12) + 1
    else:
        # For non-Whole Sign systems, use the same logic as _find_planet_house
        house_cusps = []
        for i in range(1, 13):
            cusp = chart.houses.get(f"house_{i}")
            if cusp:
                house_cusps.append((get_longitude(cusp), i))

        # Sort by longitude
        house_cusps.sort(key=lambda x: x[0])

        # Find which house the planet falls in
        for i, (cusp_lon, house_num) in enumerate(house_cusps):
            next_cusp_lon = house_cusps[(i + 1) % len(house_cusps)][0]

            if cusp_lon < next_cusp_lon:
                if cusp_lon <= transit_longitude < next_cusp_lon:
                    return house_num
            else:
                if transit_longitude >= cusp_lon or transit_longitude < next_cusp_lon:
                    return house_num

        # Fallback: if we didn't find a match, return 1
        return 1

    return house_number
