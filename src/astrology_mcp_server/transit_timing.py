"""Timing utilities for transit calculations with exact interpolation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

from astrology.core.ephemeris import Planet, PlanetPosition, get_planet_position
from astrology.core.calendar import gregorian_to_julian_day


def calculate_orb_at_time(
    transiting_planet: Planet,
    natal_position: PlanetPosition,
    dt: datetime,
    zodiac_type: str = "tropical"
) -> float:
    """Calculate the orb (angular separation) between a transiting planet and natal position at a given time.

    Args:
        transiting_planet: The planet to calculate transit for
        natal_position: The natal position (PlanetPosition)
        dt: The datetime to calculate at
        zodiac_type: "tropical" or "sidereal"

    Returns:
        Orb size in degrees (0-180)
    """
    # Calculate Julian Day
    jd = gregorian_to_julian_day(dt.year, dt.month, dt.day, dt.hour)
    
    # Get transiting position
    transiting_pos = get_planet_position(transiting_planet, jd.jd, zodiac_type)
    
    # Calculate angular separation
    orb = abs(transiting_pos.longitude - natal_position.longitude)
    
    # Normalize to 0-180
    if orb > 180:
        orb = 360 - orb
    
    return orb


def find_exact_conjunction_time(
    transiting_planet: Planet,
    natal_position: PlanetPosition,
    start_dt: datetime,
    end_dt: datetime,
    zodiac_type: str = "tropical",
    precision_hours: float = 0.1
) -> Tuple[datetime, float]:
    """Find the exact time when a transiting planet conjoins a natal position (orb = 0°).

    Uses bisection method to find the moment of exact conjunction within the specified time range.

    Args:
        transiting_planet: The planet to calculate transit for
        natal_position: The natal position (PlanetPosition)
        start_dt: Start of search window
        end_dt: End of search window
        zodiac_type: "tropical" or "sidereal"
        precision_hours: Desired precision in hours (default 0.1 = 6 minutes)

    Returns:
        Tuple of (exact_datetime, orb_at_exact_time)
    """
    # Check if conjunction occurs in this range by looking for 0° orb crossing
    # We need to find when the orb reaches minimum
    
    best_dt = start_dt
    best_orb = calculate_orb_at_time(transiting_planet, natal_position, start_dt, zodiac_type)
    
    # First, do a coarse search to find the approximate time of minimum orb
    current_dt = start_dt
    hour_step = 1
    
    while current_dt <= end_dt:
        orb = calculate_orb_at_time(transiting_planet, natal_position, current_dt, zodiac_type)
        if orb < best_orb:
            best_orb = orb
            best_dt = current_dt
        current_dt += timedelta(hours=hour_step)
    
    # Now refine around the best time using bisection
    # Create a search window around the best time
    search_start = max(start_dt, best_dt - timedelta(hours=12))
    search_end = min(end_dt, best_dt + timedelta(hours=12))
    
    # Bisection method: find when orb is smallest
    # We'll use a simple refinement approach with decreasing step sizes
    
    current_dt = search_start
    step = timedelta(hours=1)
    
    while step > timedelta(minutes=precision_hours * 60):
        # Try points around current best
        test_times = [
            best_dt - step,
            best_dt,
            best_dt + step
        ]
        
        for test_dt in test_times:
            if search_start <= test_dt <= search_end:
                orb = calculate_orb_at_time(transiting_planet, natal_position, test_dt, zodiac_type)
                if orb < best_orb:
                    best_orb = orb
                    best_dt = test_dt
        
        # Reduce step size
        step = step / 2
    
    return best_dt, best_orb


def find_exact_aspect_time(
    transiting_planet: Planet,
    natal_position: PlanetPosition,
    aspect_degrees: float,
    start_dt: datetime,
    end_dt: datetime,
    zodiac_type: str = "tropical",
    precision_hours: float = 0.1
) -> Tuple[datetime, float]:
    """Find the exact time when a transiting planet forms an aspect with a natal position.

    Uses bisection method to find the moment when the orb reaches 0° for the specified aspect.

    Args:
        transiting_planet: The planet to calculate transit for
        natal_position: The natal position (PlanetPosition)
        aspect_degrees: The target aspect angle (0 for conjunction, 180 for opposition, etc.)
        start_dt: Start of search window
        end_dt: End of search window
        zodiac_type: "tropical" or "sidereal"
        precision_hours: Desired precision in hours (default 0.1 = 6 minutes)

    Returns:
        Tuple of (exact_datetime, orb_at_exact_time)
    """
    # For a given aspect angle, we need to find when the angular separation
    # equals that angle (modulo 360)
    
    def calculate_aspect_orb(dt: datetime) -> float:
        """Calculate how close we are to the exact aspect at this time."""
        jd = gregorian_to_julian_day(dt.year, dt.month, dt.day, dt.hour)
        transiting_pos = get_planet_position(transiting_planet, jd.jd, zodiac_type)
        
        # Calculate angular separation
        raw_orb = transiting_pos.longitude - natal_position.longitude
        
        # Normalize to 0-360
        raw_orb = raw_orb % 360
        
        # Calculate distance to target aspect
        # This gives us the orb size (how far we are from exact aspect)
        orb = abs(raw_orb - aspect_degrees)
        
        # Also check the wrap-around case
        orb_wrap = abs(raw_orb - (aspect_degrees + 360))
        orb_wrap2 = abs(raw_orb - (aspect_degrees - 360))
        
        return min(orb, orb_wrap, orb_wrap2)
    
    # First, find approximate time
    best_dt = start_dt
    best_orb = calculate_aspect_orb(start_dt)
    
    current_dt = start_dt
    hour_step = 1
    
    while current_dt <= end_dt:
        orb = calculate_aspect_orb(current_dt)
        if orb < best_orb:
            best_orb = orb
            best_dt = current_dt
        current_dt += timedelta(hours=hour_step)
    
    # Refine using bisection-like approach
    search_start = max(start_dt, best_dt - timedelta(hours=12))
    search_end = min(end_dt, best_dt + timedelta(hours=12))
    
    step = timedelta(hours=1)
    
    while step > timedelta(minutes=precision_hours * 60):
        test_times = [
            best_dt - step,
            best_dt,
            best_dt + step
        ]
        
        for test_dt in test_times:
            if search_start <= test_dt <= search_end:
                orb = calculate_aspect_orb(test_dt)
                if orb < best_orb:
                    best_orb = orb
                    best_dt = test_dt
        
        step = step / 2
    
    return best_dt, best_orb


def interpolate_exact_moment(
    transiting_planet: Planet,
    natal_position: PlanetPosition,
    start_dt: datetime,
    end_dt: datetime,
    zodiac_type: str = "tropical",
    precision_minutes: float = 6
) -> Tuple[datetime, float]:
    """Find the exact moment of closest approach between transiting and natal positions.

    Uses a two-phase approach:
    1. Coarse scan (1-hour steps) to find approximate window of minimum orb
    2. Fine refinement using bisection around that window

    Args:
        transiting_planet: The planet to calculate transit for
        natal_position: The natal position (PlanetPosition)
        start_dt: Start of search window
        end_dt: End of search window
        zodiac_type: "tropical" or "sidereal"
        precision_minutes: Desired precision in minutes (default 6)

    Returns:
        Tuple of (exact_datetime, orb_at_exact_time)
    """
    # Phase 1: Coarse scan to find window with minimum orb
    current_dt = start_dt
    best_dt = start_dt
    best_orb = calculate_orb_at_time(transiting_planet, natal_position, start_dt, zodiac_type)
    
    # Track if we see orb decreasing then increasing (indicating a minimum)
    orb_readings = [(start_dt, best_orb)]
    
    while current_dt <= end_dt:
        orb = calculate_orb_at_time(transiting_planet, natal_position, current_dt, zodiac_type)
        orb_readings.append((current_dt, orb))
        if orb < best_orb:
            best_orb = orb
            best_dt = current_dt
        current_dt += timedelta(hours=1)
    
    # If the minimum orb is very large (> 90°), we're not actually finding a conjunction
    # In this case, return the best we found but with a warning flag
    # For practical purposes, if orb > 90°, the transiting planet never gets close
    
    # Phase 2: Refine around the best time
    # Create a search window of +/- 12 hours centered on best_dt
    search_start = max(start_dt, best_dt - timedelta(hours=12))
    search_end = min(end_dt, best_dt + timedelta(hours=12))
    
    # Use bisection-style refinement with decreasing step sizes
    step_hours = 12
    current_orb = best_orb
    
    while step_hours >= precision_minutes / 60:
        # Try points at current step size around best time
        test_points = [
            best_dt - timedelta(hours=step_hours),
            best_dt - timedelta(hours=step_hours/2),
            best_dt,
            best_dt + timedelta(hours=step_hours/2),
            best_dt + timedelta(hours=step_hours)
        ]
        
        for test_dt in test_points:
            if search_start <= test_dt <= search_end:
                orb = calculate_orb_at_time(transiting_planet, natal_position, test_dt, zodiac_type)
                if orb < current_orb:
                    current_orb = orb
                    best_dt = test_dt
        
        # Reduce step size
        step_hours /= 2
    
    return best_dt, current_orb
