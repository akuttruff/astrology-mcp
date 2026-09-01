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


def _convert_to_zonal(longitude: float, zodiac_type: str = "tropical", jd: float | None = None) -> ZonalPosition:
    """Convert longitude to zonal position (sign and degree).

    Args:
        longitude: Longitude in degrees (0-360)
        zodiac_type: "tropical" or "sidereal"
        jd: Julian Day (optional, required for accurate sidereal calculations)

    Returns:
        ZonalPosition with sign and degree information
    """
    # Normalize longitude to 0-360
    longitude = longitude % 360

    # For tropical zodiac, start from 0° Aries (equinox)
    # For sidereal, we'd need to subtract ayanamsa
    if zodiac_type == "sidereal":
        # Use the provided JD for ayanamsa calculation, or default to J2000.0
        if jd is not None:
            ayanamsa = calculate_ayanamsa(jd)
        else:
            # Fallback: use approximate Lahiri ayanamsa (24° at J2000.0)
            # This is acceptable for most purposes
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
        # Try common ephemeris paths (removed hardcoded user-specific path)
        try_paths = [
            "/usr/share/swisseph",
            "./ephe",
            "/opt/swisseph",
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

    # Calculate houses using Placidus first to get accurate ASC and MC
    try:
        cusps_placidus, ascmc_placidus = swe.houses(
            jd, latitude, longitude, b'P'
        )
    except Exception as e:
        raise RuntimeError(f"Failed to calculate houses: {e}")

    # Parse Placidus results for angles (ASC, MC, etc.)
    ascendant = _convert_to_zonal(ascmc_placidus[0])
    midheaven = _convert_to_zonal(ascmc_placidus[1])
    descendant = _convert_to_zonal(ascmc_placidus[2])
    ic = _convert_to_zonal(ascmc_placidus[3])

    # Parse results for house cusps using the requested system
    houses = {}

    if house_system == "W":
        # Whole Sign houses: each house starts at 0° of its sign
        # House 1 starts at the sign where ASC falls
        asc_sign_index = int(ascendant.longitude // 30)

        for i in range(12):
            house_num = i + 1
            # House i starts at (asc_sign_index + i - 1) % 12
            sign_index = (asc_sign_index + i) % 12
            # House cusp is at 0° of that sign
            house_longitude = sign_index * 30.0
            houses[f"house_{house_num}"] = _convert_to_zonal(house_longitude)

        # Descendant and IC are 180° from ASC and MC (for Whole Sign consistency)
        descendant_lon = (ascendant.longitude + 180) % 360
        houses["descendant"] = _convert_to_zonal(descendant_lon)
        ic_lon = (midheaven.longitude + 180) % 360
        houses["ic"] = _convert_to_zonal(ic_lon)
    else:
        # Other house systems: use their actual cusps
        try:
            cusps, ascmc = swe.houses(
                jd, latitude, longitude, house_system.encode()
            )
            for i, cusp in enumerate(cusps):
                house_num = i + 1
                houses[f"house_{house_num}"] = _convert_to_zonal(cusp)

            # Store ASC and MC from the actual calculation
            houses["ascendant"] = _convert_to_zonal(ascmc[0])
            houses["midheaven"] = _convert_to_zonal(ascmc[1])
            houses["descendant"] = _convert_to_zonal(ascmc[2])
            houses["ic"] = _convert_to_zonal(ascmc[3])
        except Exception as e:
            # Fallback to Placidus if requested system fails
            for i, cusp in enumerate(cusps_placidus):
                house_num = i + 1
                houses[f"house_{house_num}"] = _convert_to_zonal(cusp)
            houses["ascendant"] = ascendant
            houses["midheaven"] = midheaven

    # Store ASC and MC directly (for backward compatibility)
    houses["ascendant"] = ascendant
    houses["mc"] = midheaven

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


def get_moon_phase(jd: float) -> tuple[str, float, int]:
    """Calculate the current moon phase.

    Args:
        jd: Julian Day

    Returns:
        Tuple of (phase_name, illumination_percent, synodic_age)
        phase_name: Current phase (New Moon, First Quarter, Full Moon, Last Quarter, etc.)
        illumination_percent: Percentage of moon illuminated (0-100)
        synodic_age: Days since last new moon (0-29.53)
    """
    # Synodic month length in days
    synodic_month = 29.53058867
    
    # Reference new moon at JD 2451550.3 (January 6, 2000, 18:14 UT)
    reference_new_moon = 2451550.3
    
    # Calculate days since reference new moon
    days_since_new = jd - reference_new_moon
    
    # Calculate position in synodic cycle (0-1)
    cycle_position = (days_since_new % synodic_month) / synodic_month
    
    # Calculate synodic age in days
    synodic_age = cycle_position * synodic_month
    
    # Calculate illumination (0-100%)
    # Illumination is 0% at new moon, 50% at quarters, 100% at full moon
    illumination = 50 * (1 - math.cos(2 * math.pi * cycle_position))
    
    # Determine phase name based on cycle position
    if synodic_age < 1.845:
        phase_name = "New Moon"
    elif synodic_age < 5.539:
        phase_name = "Waxing Crescent"
    elif synodic_age < 9.231:
        phase_name = "First Quarter"
    elif synodic_age < 12.924:
        phase_name = "Waxing Gibbous"
    elif synodic_age < 16.617:
        phase_name = "Full Moon"
    elif synodic_age < 20.310:
        phase_name = "Waning Gibbous"
    elif synodic_age < 24.003:
        phase_name = "Last Quarter"
    elif synodic_age < 27.695:
        phase_name = "Waning Crescent"
    else:
        phase_name = "New Moon"
    
    return phase_name, round(illumination, 2), int(synodic_age)


def get_moon_phase_angle(jd: float) -> tuple[float, float]:
    """Calculate moon phase angle and sun-moon separation.

    Args:
        jd: Julian Day

    Returns:
        Tuple of (phase_angle_degrees, sun_moon_separation_degrees)
        phase_angle: Angle between sun and moon as seen from Earth (0=new, 180=full)
        separation: Direct angular separation between sun and moon
    """
    from astrology.core.ephemeris import get_planet_position, Planet
    
    # Get sun and moon positions
    sun_pos = get_planet_position(Planet.SUN, jd)
    moon_pos = get_planet_position(Planet.MOON, jd)
    
    # Calculate angular separation
    separation = abs(moon_pos.longitude - sun_pos.longitude)
    if separation > 180:
        separation = 360 - separation
    
    # Phase angle is the same as separation for moon phases
    # 0° = new moon, 180° = full moon
    phase_angle = separation
    
    return round(phase_angle, 2), round(separation, 2)


def find_next_moon_phase(jd: float, target_phase: str) -> tuple[float, str]:
    """Find the next occurrence of a specific moon phase.

    Args:
        jd: Starting Julian Day
        target_phase: Target phase ("New Moon", "First Quarter", "Full Moon", "Last Quarter")

    Returns:
        Tuple of (jd_of_phase, phase_name)
    """
    # Synodic month length in days
    synodic_month = 29.53058867
    
    # Phase offsets in synodic cycle (fraction of cycle)
    phase_offsets = {
        "New Moon": 0.0,
        "First Quarter": 0.25,
        "Full Moon": 0.5,
        "Last Quarter": 0.75,
    }
    
    if target_phase not in phase_offsets:
        return jd, "Unknown"
    
    # Get current cycle position
    reference_new_moon = 2451550.3
    days_since_new = jd - reference_new_moon
    current_cycle_pos = (days_since_new % synodic_month) / synodic_month
    
    # Calculate target cycle position
    target_cycle_pos = phase_offsets[target_phase]
    
    # Find next occurrence
    if current_cycle_pos < target_cycle_pos:
        days_until = (target_cycle_pos - current_cycle_pos) * synodic_month
    else:
        days_until = (1 - current_cycle_pos + target_cycle_pos) * synodic_month
    
    next_jd = jd + days_until
    
    return next_jd, target_phase


def scan_moon_phases(jd_start: float, jd_end: float) -> list[dict[str, Any]]:
    """Scan for moon phases within a date range.

    Args:
        jd_start: Starting Julian Day
        jd_end: Ending Julian Day

    Returns:
        List of phase events with date, name, and illumination
    """
    from astrology.core.calendar import julian_day_to_datetime
    
    phases = []
    current_jd = jd_start
    
    # Check approximately every 3 days (moon phase changes significantly)
    while current_jd <= jd_end:
        phase_name, illumination, _ = get_moon_phase(current_jd)
        
        # Check if this is a major phase
        if phase_name in ["New Moon", "First Quarter", "Full Moon", "Last Quarter"]:
            # Refine the exact time using binary search
            refined_jd = _refine_moon_phase_time(current_jd, phase_name)
            
            if jd_start <= refined_jd <= jd_end:
                date_time = julian_day_to_datetime(refined_jd)
                phases.append({
                    "phase": phase_name,
                    "date": date_time.isoformat(),
                    "illumination": illumination,
                })
        
        current_jd += 3
    
    return phases


def _refine_moon_phase_time(jd_start: float, target_phase: str, tolerance: float = 0.001) -> float:
    """Refine moon phase time using binary search.

    Args:
        jd_start: Starting Julian Day
        target_phase: Target phase to refine
        tolerance: Time tolerance in days (default 1.44 minutes)

    Returns:
        Refined Julian Day for the phase
    """
    synodic_month = 29.53058867
    
    # Target cycle position for the phase
    phase_offsets = {
        "New Moon": 0.0,
        "First Quarter": 0.25,
        "Full Moon": 0.5,
        "Last Quarter": 0.75,
    }
    
    target_cycle_pos = phase_offsets.get(target_phase, 0.0)
    reference_new_moon = 2451550.3
    
    # Binary search for exact time
    low = jd_start - 1
    high = jd_start + 1
    
    for _ in range(50):  # Max iterations
        mid = (low + high) / 2
        
        # Calculate current cycle position at mid
        days_since_new = mid - reference_new_moon
        cycle_pos = (days_since_new % synodic_month) / synodic_month
        
        # Adjust for cycle wrapping
        if cycle_pos < 0:
            cycle_pos += 1
        
        # Calculate error
        error = cycle_pos - target_cycle_pos
        
        # Adjust for cycle wrapping in error
        if error > 0.5:
            error -= 1
        elif error < -0.5:
            error += 1
        
        if abs(error) < tolerance / synodic_month:
            return mid
        
        # Binary search adjustment
        if error < 0:
            low = mid
        else:
            high = mid
    
    return (low + high) / 2


def find_void_of_course_periods(jd_start: float, jd_end: float, 
                                 natal_chart_data: dict | None = None) -> list[dict[str, Any]]:
    """Find void-of-course moon periods within a date range.

    A moon is void of course when it has completed all its major aspects in a sign
    and is about to enter the next sign. We detect this by finding when the moon
    changes signs.

    Args:
        jd_start: Starting Julian Day
        jd_end: Ending Julian Day
        natal_chart_data: Optional natal chart data for aspect-based VoC detection

    Returns:
        List of void-of-course periods with start/end times and last aspect info
    """
    from astrology.core.calendar import julian_day_to_datetime
    
    periods = []
    
    # Find all moon sign changes in the range by scanning with larger steps
    current_jd = jd_start
    
    while current_jd < jd_end:
        # Get moon position at this time
        # get_planet_position and Planet are available from module scope
        moon_pos = get_planet_position(Planet.MOON, current_jd)
        
        # Find what sign the moon is in
        current_sign_index = int(moon_pos.longitude // 30)
        
        # Find next sign change - search up to 3 days ahead (moon takes ~2.5 days per sign)
        next_sign_jd = _find_next_sign_change(current_jd, Planet.MOON, max_search_days=3.5)
        
        # Check if this sign change is actually a transition to the next sign
        end_pos = get_planet_position(Planet.MOON, next_sign_jd)
        end_sign_index = int(end_pos.longitude // 30)
        
        # The sign should have changed
        expected_next_sign = (current_sign_index + 1) % 12
        
        if next_sign_jd <= jd_end and end_sign_index == expected_next_sign:
            # Moon will change signs - find the exact transition time using binary search
            actual_transition = _binary_search_sign_change(
                current_jd, next_sign_jd, Planet.MOON, expected_next_sign
            )
            
            if jd_start <= actual_transition <= jd_end:
                start_time = julian_day_to_datetime(current_jd)
                end_time = julian_day_to_datetime(actual_transition)
                
                periods.append({
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "planet": "Moon",
                    "from_sign": ZODIAC_NAMES[current_sign_index],
                    "to_sign": ZODIAC_NAMES[end_sign_index],
                })
                
                # Move to just after the transition to find next one
                current_jd = actual_transition + 0.1  # ~2.4 hours after transition
            else:
                break
        elif next_sign_jd > current_jd + 3.5:
            # No sign change within reasonable time - something is wrong
            break
        else:
            # Move forward and try again
            current_jd += 1.0  # 1 day
    
    return periods


def _find_next_sign_change(jd_start: float, planet: Planet, max_search_days: float = 3.0) -> float:
    """Find the next time a planet changes signs.

    Args:
        jd_start: Starting Julian Day
        planet: The planet to track
        max_search_days: Maximum days to search for sign change

    Returns:
        Julian Day when planet enters next sign, or jd_start + max_search_days if not found
    """
    # get_planet_position is available from module scope
    current_pos = get_planet_position(planet, jd_start)
    current_sign_index = int(current_pos.longitude // 30)
    
    # Search for sign change - check every 2 hours initially
    search_jd = jd_start + 0.1  # Start 2.4 hours later
    step = 0.0833  # ~2 hours in days
    
    while search_jd <= jd_start + max_search_days:
        next_pos = get_planet_position(planet, search_jd)
        next_sign_index = int(next_pos.longitude // 30)
        
        if next_sign_index != current_sign_index:
            # Sign changed - return this point
            return search_jd
        
        search_jd += step
    
    return jd_start + max_search_days


def _binary_search_sign_change(jd_low: float, jd_high: float, planet: Planet, 
                                 target_sign_index: int) -> float:
    """Binary search for exact sign change time.

    Args:
        jd_low: Lower bound Julian Day
        jd_high: Upper bound Julian Day
        planet: The planet to track
        target_sign_index: The sign index we're transitioning TO

    Returns:
        Refined Julian Day of sign change
    """
    for _ in range(40):  # Max iterations
        jd_mid = (jd_low + jd_high) / 2
        
        pos = get_planet_position(planet, jd_mid)
        sign_index = int(pos.longitude // 30)
        
        if sign_index == target_sign_index:
            jd_high = jd_mid
        else:
            jd_low = jd_mid
        
        if jd_high - jd_low < 0.0001:  # ~1 minute precision
            break
    
    return (jd_low + jd_high) / 2
