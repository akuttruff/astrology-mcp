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

# Import transit timing module
from .transit_timing import (
    bisection_solver,
    signed_angular_difference_v2,
)


class TransitEvent(NamedTuple):
    """A transit event between a transiting planet and natal planet/point."""
    planet: Planet  # Transiting planet
    natal_planet: Planet  # Natal planet being transited
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

    def get_transit_house(self, planet: Planet) -> int | None:
        """Get the house number for a transiting planet.

        Args:
            planet: The transiting planet

        Returns:
            House number (1-12) or None if planet not found
        """
        from ..charts.chart import get_planet_transit_house

        if planet not in self.transiting_planets:
            return None

        transit_pos = self.transiting_planets[planet]
        return get_planet_transit_house(self.natal_chart, transit_pos.longitude)


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
            # Extract longitude value - PlanetPosition.longitude is always a plain float
            natal_lon = natal_pos.longitude
            transit_lon = transiting_pos.longitude

            event = TransitEvent(
                planet=planet,
                natal_planet=natal_planet,
                natal_position=natal_lon,  # Longitude in degrees (0-360)
                transit_position=transit_lon,  # Longitude in degrees (0-360)
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
        from datetime import timezone
        current_datetime = datetime.now(timezone.utc)

    # Get current planetary positions
    jd = gregorian_to_julian_day(
        current_datetime.year,
        current_datetime.month,
        current_datetime.day + (current_datetime.hour + current_datetime.minute / 60 + current_datetime.second / 3600) / 24
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
                transiting_planet_pos.longitude,
                natal_lon
            )
            aspect_type_found, exact_angle = aspect

            # Calculate orb
            diff = abs((transiting_planet_pos.longitude - natal_lon) % 360)
            if diff > 180:
                diff = 360 - diff

            orb = abs(diff - exact_angle)
            max_orb = DEFAULT_ORBS.get(aspect_type_found, 8.0)

            if orb <= max_orb:
                if aspect_type is None or aspect_type == aspect_type_found:
                    aspects.append(TransitEvent(
                        planet=transit_planet,
                        natal_position=natal_lon,
                        transit_position=transiting_planet_pos.longitude,
                        aspect_type=aspect_type_found,
                        orb=orb,
                    ))

        if aspects:
            results.append(TransitConfiguration(
                date=check_date,
                planet=transit_planet,
                transiting_position=transiting_planet_pos.longitude,
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


# =============================================================================
# Date-Range Transit Scanning (Tier 1 - eliminates workarounds)
# =============================================================================

def refine_transit_with_bisection(
    transit_planet: Planet,
    natal_planet: Planet,
    natal_lon: float,
    aspect_type: AspectType,
    exact_angle: float,
    bracket_start: datetime,
    bracket_end: datetime,
) -> dict:
    """Refine a transit event using bisection to find exact timing.

    Args:
        transit_planet: The transiting planet
        natal_planet: The natal planet being transited
        natal_lon: Natal longitude (0-360)
        aspect_type: The type of aspect
        exact_angle: Exact angle for the aspect (0, 90, 120, 180, etc.)
        bracket_start: Start of time bracket
        bracket_end: End of time bracket

    Returns:
        Dict with exact timing info from bisection
    """
    from ..core.ephemeris import get_planet_position

    def transit_lon_at_jd(jd: float) -> float:
        """Get transiting planet longitude at given Julian Day."""
        pos = get_planet_position(transit_planet, jd)
        return pos.longitude

    # Convert bracket to JD
    start_jd = gregorian_to_julian_day(
        bracket_start.year, bracket_start.month,
        bracket_start.day + bracket_start.hour / 24 + bracket_start.minute / 1440
    ).jd

    end_jd = gregorian_to_julian_day(
        bracket_end.year, bracket_end.month,
        bracket_end.day + bracket_end.hour / 24 + bracket_end.minute / 1440
    ).jd

    # Run bisection solver
    result = bisection_solver(
        transit_lon_func=transit_lon_at_jd,
        natal_lon=natal_lon,
        exact_angle=exact_angle,
        t0_jd=start_jd,
        t1_jd=end_jd,
    )

    return result.to_dict()


def calculate_transit_for_date_range(
    natal_chart: NatalChart,
    start_date: datetime,
    end_date: datetime,
    min_orb: float = 2.0,
    refine_with_bisection: bool = True,
) -> list[TransitEvent]:
    """Calculate all transits in a date range, deduped and structured.

    This function samples at 1-hour intervals to find potential transit events,
    then optionally refines the exact timing using bisection interpolation.

    Args:
        natal_chart: The natal chart
        start_date: Start date for scanning
        end_date: End date for scanning
        min_orb: Minimum orb to include (smaller = more significant)
        refine_with_bisection: If True, use bisection to find exact timing

    Returns:
        List of TransitEvent objects with enhanced timing info
    """
    from ..core.ephemeris import get_all_planets, get_planet_position
    from datetime import timedelta

    # Hourly sampling for better accuracy (Moon moves ~0.6°/hr)
    sample_interval_hours = 1

    results = []
    seen_events = set()  # For deduplication

    current_date = start_date
    while current_date <= end_date:
        # Get Julian Day for this date
        jd = gregorian_to_julian_day(
            current_date.year,
            current_date.month,
            current_date.day,
            current_date.hour + current_date.minute/60
        )

        # Get transiting positions for all planets
        transiting_positions = get_all_planets(jd.jd)

        # Check aspects for each transiting planet to natal positions
        major_planets = [
            Planet.SUN, Planet.MOON,
            Planet.MERCURY, Planet.VENUS, Planet.MARS,
            Planet.JUPITER, Planet.SATURN,
            Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO
        ]

        for transit_planet in major_planets:
            if transit_planet not in transiting_positions:
                continue

            transit_pos = transiting_positions[transit_planet]

            # Build natal positions dict
            natal_positions = {}
            for planet, pos in natal_chart.planets.items():
                natal_positions[planet] = pos

            if natal_chart.ascendant:
                natal_positions[Planet.ASCENDANT] = PlanetPosition(
                    planet=Planet.ASCENDANT,
                    longitude=natal_chart.ascendant.longitude,
                    latitude=0.0, distance=1.0, retrograde=False, motion_speed=0.0
                )
            if natal_chart.midheaven:
                natal_positions[Planet.MC] = PlanetPosition(
                    planet=Planet.MC,
                    longitude=natal_chart.midheaven.longitude,
                    latitude=0.0, distance=1.0, retrograde=False, motion_speed=0.0
                )

            # Check aspects to each natal planet/point
            for natal_planet, natal_pos in natal_positions.items():
                aspect = calculate_aspect(
                    transit_pos.longitude,
                    natal_pos.longitude
                )

                if aspect:
                    aspect_type, exact_angle = aspect

                    # Calculate orb
                    diff = abs((transit_pos.longitude - natal_pos.longitude) % 360)
                    if diff > 180:
                        diff = 360 - diff

                    orb = abs(diff - exact_angle)

                    if orb <= min_orb:
                        # Create deduplication key (include hour for finer granularity)
                        key = (
                            transit_planet,
                            natal_planet,
                            aspect_type,
                            current_date.date().isoformat(),
                            current_date.hour  # Include hour for dedup
                        )

                        if key not in seen_events:
                            seen_events.add(key)

                            # Store sample data for potential bisection refinement
                            event_info = {
                                "planet": transit_planet,
                                "natal_planet": natal_planet,
                                "natal_position": natal_pos.longitude,
                                "transit_position": transit_pos.longitude,
                                "aspect_type": aspect_type,
                                "orb": orb,
                                "sample_time": current_date,
                            }
                            results.append(event_info)

        # Advance to next sample interval
        current_date += timedelta(hours=sample_interval_hours)

    # Sort by orb (most significant first - smallest orb)
    results.sort(key=lambda e: e["orb"])

    # Group events by (planet, natal_planet, aspect_type) to find peak orb
    grouped: dict[tuple, list[dict]] = {}
    for event in results:
        key = (event["planet"], event["natal_planet"], event["aspect_type"])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(event)

    # For each group, find the best sample and refine with bisection
    final_events = []
    for key, group in grouped.items():
        transit_planet, natal_planet, aspect_type = key

        # Find sample with minimum orb (closest to exact)
        best_sample = min(group, key=lambda e: e["orb"])
        sample_time = best_sample["sample_time"]

        # Get bracket samples (neighbors of best)
        best_idx = group.index(best_sample)

        if refine_with_bisection and len(group) >= 3:
            # Get bracket from neighbors
            left_idx = max(0, best_idx - 1)
            right_idx = min(len(group) - 1, best_idx + 1)

            bracket_start = group[left_idx]["sample_time"]
            bracket_end = group[right_idx]["sample_time"]

            # Get exact angle for aspect type
            max_orb = DEFAULT_ORBS.get(aspect_type, 8.0)

            # Determine exact angle from max orb (conjunction=8°, square=5°, etc.)
            # This is approximate - we use the max orb as reference
            aspect_angles = {
                AspectType.CONJUNCTION: 0.0,
                AspectType.OPPOSITION: 180.0,
                AspectType.SQUARE: 90.0,
                AspectType.TRINE: 120.0,
                AspectType.SEXTILE: 60.0,
            }
            exact_angle = aspect_angles.get(aspect_type, 0.0)

            # Run bisection refinement
            timing_info = refine_transit_with_bisection(
                transit_planet=transit_planet,
                natal_planet=natal_planet,
                natal_lon=best_sample["natal_position"],
                aspect_type=aspect_type,
                exact_angle=exact_angle,
                bracket_start=bracket_start,
                bracket_end=bracket_end,
            )

            # Update event with timing info
            refined_event = best_sample.copy()
            refined_event["timing_info"] = timing_info

            # Create TransitEvent with refined information
            event = TransitEvent(
                planet=refined_event["planet"],
                natal_planet=refined_event["natal_planet"],
                natal_position=refined_event["natal_position"],
                transit_position=refined_event["transit_position"],
                aspect_type=refined_event["aspect_type"],
                orb=round(timing_info.get("min_orb", refined_event["orb"]), 4),
            )
        else:
            # No refinement - use best sample
            event = TransitEvent(
                planet=best_sample["planet"],
                natal_planet=best_sample["natal_planet"],
                natal_position=best_sample["natal_position"],
                transit_position=best_sample["transit_position"],
                aspect_type=best_sample["aspect_type"],
                orb=best_sample["orb"],
            )

        final_events.append(event)

    # Sort by orb one more time after refinement
    final_events.sort(key=lambda e: e.orb)

    return final_events


def transit_to_dict(event: TransitEvent, natal_chart: NatalChart) -> dict:
    """Convert a TransitEvent to structured JSON with full position info.

    Args:
        event: The TransitEvent
        natal_chart: The natal chart for context

    Returns:
        Structured dictionary with all position info
    """
    from ..charts.chart import get_planet_sign, get_planet_degree

    result = {
        "transiting_planet": {
            "name": event.planet.name,
            "sign": get_planet_sign(event.planet, event.transit_position),
            "degree": round(get_planet_degree(event.planet, event.transit_position), 2),
            "longitude": round(event.transit_position, 4)
        },
        "natal_planet": {
            "name": event.natal_planet.name,
            "sign": get_planet_sign(event.natal_planet, event.natal_position),
            "degree": round(get_planet_degree(event.natal_planet, event.natal_position), 2),
            "longitude": round(event.natal_position, 4)
        },
        "aspect_type": event.aspect_type.name,
        "orb": round(event.orb, 4),
        "exact_angle": float(DEFAULT_ORBS.get(event.aspect_type, 8.0))
    }

    # Add peak orb window with timing info
    result["peak_orb_window"] = get_peak_orb_window(event)

    return result


def transit_report_to_json(events: list[TransitEvent], natal_chart: NatalChart) -> dict:
    """Convert transit events to full structured JSON response.

    Args:
        events: List of TransitEvent objects
        natal_chart: The natal chart

    Returns:
        Complete structured JSON response with no truncation
    """
    return {
        "total_events": len(events),
        "events": [transit_to_dict(e, natal_chart) for e in events],
        "metadata": {
            "has_more": False,  # No truncation
            "page_token": None,
            "narrative_summary": None  # User can generate their own
        }
    }


def get_peak_orb_window(event: TransitEvent, timing_info: dict | None = None) -> dict:
    """Get the peak orb window for a transit event.

    Args:
        event: The TransitEvent
        timing_info: Optional dict with bisection timing results

    Returns:
        Dict with exact timestamp and orb range
    """
    if timing_info:
        # Use bisection results when available
        exact_time = timing_info.get("exact_time")
        min_orb = timing_info.get("min_orb", event.orb)
        aspect_status = timing_info.get("aspect_status", "UNKNOWN")

        return {
            "exact_aspect_orb": round(min_orb, 4),
            "orb_range": {
                "min": round(max(0, min_orb - 0.5), 4),
                "max": round(min_orb + 0.5, 4)
            },
            "within_1_degree_window": {
                "start": round(max(0, min_orb - 1.0), 4),
                "end": round(min_orb + 1.0, 4)
            },
            "exact_time": exact_time,
            "aspect_status": aspect_status,
        }
    else:
        # Fallback for events without bisection timing
        return {
            "exact_aspect_orb": round(event.orb, 4),
            "orb_range": {
                "min": round(max(0, event.orb - 0.5), 4),
                "max": round(event.orb + 0.5, 4)
            },
            "within_1_degree_window": {
                "start": round(max(0, event.orb - 1.0), 4),
                "end": round(event.orb + 1.0, 4)
            },
        }


# =============================================================================
# Significance Weighting (Tier 2 - interpretation support)
# =============================================================================

def calculate_transit_significance(
    event: TransitEvent,
    natal_chart: NatalChart | None = None
) -> float:
    """Calculate a significance score for a transit event.
    
    Args:
        event: The TransitEvent
        natal_chart: Optional natal chart for luminaries/angles check

    Returns:
        Significance score (0-1, higher = more significant)
        
    Based on:
    - Aspect quality: exact aspects > quincunx
    - Orb size: smaller orb = more significant  
    - Transiting planet speed: faster planets create shorter, sharper transits
    - Luminaries/angles: Sun/Moon/Ascendant/MC aspects are more impactful
    """
    from ..core.ephemeris import DEFAULT_ORBS
    
    score = 1.0
    
    # Factor 1: Aspect quality (exact aspects > quincunx)
    # Exact aspects: conjunction, opposition, square, trine, sextile
    exact_aspects = [
        AspectType.CONJUNCTION,
        AspectType.OPPOSITION, 
        AspectType.SQUARE,
        AspectType.TRINE,
        AspectType.SEXTILE
    ]
    
    if event.aspect_type not in exact_aspects:
        score *= 0.7  # Less significant for non-exact aspects
    
    # Factor 2: Orb size (smaller orb = more significant)
    # Normalize to 0-1 range based on max orb for this aspect type
    max_orb = DEFAULT_ORBS.get(event.aspect_type, 8.0)
    
    if event.orb <= max_orb * 0.3:
        score *= 1.0  # Very tight orb - most significant
    elif event.orb <= max_orb * 0.5:
        score *= 0.8
    elif event.orb <= max_orb * 0.7:
        score *= 0.6
    elif event.orb <= max_orb:
        score *= 0.4
    else:
        score *= 0.2
    
    # Factor 3: Transiting planet speed
    # Faster planets = shorter, sharper transits (more impactful)
    # Order from slowest to fastest: Pluto, Neptune, Saturn, Uranus, Jupiter,
    # Mars, Venus, Mercury, Moon, Sun
    speed_ranking = {
        Planet.PLUTO: 1,
        Planet.NEPTUNE: 2,
        Planet.SATURN: 3,
        Planet.URANUS: 4,
        Planet.JUPITER: 5,
        Planet.MARS: 6,
        Planet.VENUS: 7,
        Planet.MERCURY: 8,
        Planet.MOON: 9,
        Planet.SUN: 10
    }
    
    speed_score = speed_ranking.get(event.planet, 5) / 10.0
    score *= speed_score
    
    # Factor 4: Luminaries/angles are more impactful
    luminaries = [Planet.SUN, Planet.MOON]
    angles = [Planet.ASCENDANT, Planet.MC]
    
    if event.planet in luminaries or event.natal_planet in luminaries:
        score *= 1.3  # More significant for luminaries
    if event.planet in angles or event.natal_planet in angles:
        score *= 1.2  # More significant for angles
    
    return min(1.0, score)  # Cap at 1.0


def filter_by_significance(
    events: list[TransitEvent],
    min_score: float = 0.5,
    natal_chart: NatalChart | None = None
) -> list[TransitEvent]:
    """Filter transit events by significance score.
    
    Args:
        events: List of TransitEvent objects
        min_score: Minimum significance score (0-1)
        natal_chart: Optional natal chart for calculations

    Returns:
        Filtered list of events
    """
    return [
        e for e in events
        if calculate_transit_significance(e, natal_chart) >= min_score
    ]


def add_significance_to_dict(event: TransitEvent, natal_chart: NatalChart) -> dict:
    """Add significance score to transit dict.
    
    Args:
        event: The TransitEvent
        natal_chart: The natal chart

    Returns:
        Dict with significance score included
    """
    base_dict = transit_to_dict(event, natal_chart)
    base_dict["significance_score"] = round(calculate_transit_significance(event, natal_chart), 4)
    base_dict["peak_orb_window"] = get_peak_orb_window(event)
    
    return base_dict


def transit_report_with_significance(
    events: list[TransitEvent],
    natal_chart: NatalChart,
    min_significance: float = 0.3
) -> dict:
    """Generate transit report with significance filtering and scoring.
    
    Args:
        events: List of TransitEvent objects
        natal_chart: The natal chart
        min_significance: Minimum significance score to include

    Returns:
        Complete structured JSON with significance scoring
    """
    # Calculate significance for all events
    scored_events = [
        add_significance_to_dict(e, natal_chart) for e in events
    ]
    
    # Filter by minimum significance if specified
    if min_significance > 0:
        scored_events = [
            e for e in scored_events 
            if e.get("significance_score", 0) >= min_significance
        ]
    
    return {
        "total_events": len(scored_events),
        "events": scored_events,
        "metadata": {
            "has_more": False,
            "page_token": None,
            "narrative_summary": None
        }
    }


# =============================================================================
# Grouping (Tier 2 - already partially implemented in transit.py)
# =============================================================================

def group_transits_by_house(
    events: list[TransitEvent],
    natal_chart: NatalChart
) -> dict[int, list[TransitEvent]]:
    """Group transit events by house.
    
    Args:
        events: List of TransitEvent objects
        natal_chart: The natal chart

    Returns:
        Dict mapping house numbers to lists of events
    """
    from ..charts.chart import get_planet_transit_house
    
    groups: dict[int, list[TransitEvent]] = {}
    
    for event in events:
        house = get_planet_transit_house(natal_chart, event.transit_position)
        if house:
            if house not in groups:
                groups[house] = []
            groups[house].append(event)
    
    return groups


def group_transits_by_planet(
    events: list[TransitEvent],
    natal_chart: NatalChart
) -> dict[str, list[TransitEvent]]:
    """Group transit events by transiting planet.
    
    Args:
        events: List of TransitEvent objects
        natal_chart: The natal chart (for context)

    Returns:
        Dict mapping planet names to lists of events
    """
    groups: dict[str, list[TransitEvent]] = {}
    
    for event in events:
        planet_name = event.planet.name
        if planet_name not in groups:
            groups[planet_name] = []
        groups[planet_name].append(event)
    
    return groups


def group_transits_by_aspect(
    events: list[TransitEvent],
    natal_chart: NatalChart
) -> dict[str, list[TransitEvent]]:
    """Group transit events by aspect type.
    
    Args:
        events: List of TransitEvent objects
        natal_chart: The natal chart (for context)

    Returns:
        Dict mapping aspect names to lists of events
    """
    groups: dict[str, list[TransitEvent]] = {}
    
    for event in events:
        aspect_name = event.aspect_type.name
        if aspect_name not in groups:
            groups[aspect_name] = []
        groups[aspect_name].append(event)
    
    return groups
