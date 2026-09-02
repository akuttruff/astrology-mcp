"""Exact transit timing using bisection interpolation.

This module provides functions for finding the exact moment when a transit
aspect reaches its minimum orb using bisection search on signed angular difference.

Key features:
- Bisection solver for exact aspect timing
- Signed difference calculation that handles 0°/360° wrap correctly
- Station/retrograde handling (no sign change = return best sample)
- Integration with existing scan loop in transit.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Callable

from ..core.aspects import DEFAULT_ORBS
from ..core.calendar import JulianDay, gregorian_to_julian_day, julian_day_to_datetime
from ..core.ephemeris import Planet, get_planet_position


class AspectStatus(Enum):
    """Status of a transit aspect at its exact moment."""
    EXACT = auto()  # Bisection found sign change, exact time computed
    IN_PROGRESS = auto()  # No sign change in bracket (station/retrograde)
    EXTRAPOLATED = auto()  # Best sample at window edge, extrapolated


@dataclass
class TransitTimingResult:
    """Result of bisection-based transit timing."""
    exact_time: datetime | None  # Exact moment of minimum orb (if found)
    exact_jd: float | None  # Julian Day of exact time
    extrapolated_exact: datetime | None  # Extrapolated exact if at boundary
    aspect_status: AspectStatus  # Status of the aspect
    min_orb: float  # Minimum orb found (at exact_time or best sample)
    orb_range: tuple[float, float]  # Orb range within 1° window
    clipped_at_window_boundary: bool  # True if bracket hit window edge
    warnings: list[str]  # Any warnings about the solution

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "exact_time": self.exact_time.isoformat() if self.exact_time else None,
            "exact_jd": round(self.exact_jd, 6) if self.exact_jd else None,
            "extrapolated_exact": (
                self.extrapolated_exact.isoformat() if self.extrapolated_exact else None
            ),
            "aspect_status": self.aspect_status.name,
            "min_orb": round(self.min_orb, 4),
            "orb_range": [round(v, 4) for v in self.orb_range],
            "clipped_at_window_boundary": self.clipped_at_window_boundary,
            "warnings": self.warnings,
        }


# =============================================================================
# Bisection Solver
# =============================================================================


def wrap_180(angle: float) -> float:
    """Wrap angle to -180 to +180 range.

    Args:
        angle: Angle in degrees (can be any value)

    Returns:
        Wrapped angle in -180 to +180 range
    """
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def signed_angular_difference(
    transit_lon: float,
    natal_lon: float,
    exact_angle: float,
) -> float:
    """Calculate signed angular difference for bisection.

    The sign indicates whether the transit is before or after the exact aspect.
    This handles the 0°/360° wrap correctly.

    f(t) < 0: transit longitude is "behind" the exact aspect
    f(t) > 0: transit longitude is "ahead" of the exact aspect
    f(t) = 0: exactly on the aspect

    Args:
        transit_lon: Current transiting planet longitude (0-360)
        natal_lon: Natal planet longitude (0-360)
        exact_angle: Exact aspect angle (0, 90, 120, 180, etc.)

    Returns:
        Signed difference in degrees (-180 to +180)
    """
    # Calculate the angular separation (shortest arc, 0-180)
    diff = abs((transit_lon - natal_lon) % 360)
    if diff > 180:
        diff = 360 - diff

    # Calculate orb (distance from exact aspect)
    orb = abs(diff - exact_angle)

    # Determine if we're before or after the exact aspect
    # This is the tricky part - we need signed difference

    # Get raw longitudinal difference (can be negative)
    raw_diff = (transit_lon - natal_lon) % 360

    # If raw_diff > 180, the short arc is in the opposite direction
    if raw_diff > 180:
        raw_diff -= 360

    # Now determine if we're before or after exact aspect
    # For a conjunction (exact_angle = 0):
    #   - If transit_lon < natal_lon (raw_diff negative), we're before
    #   - If transit_lon > natal_lon (raw_diff positive), we're after

    # The sign depends on the direction of motion and aspect type
    # For simplicity, we use: diff_from_exact with sign based on raw_diff

    if diff >= exact_angle:
        # We're past the exact angle (diff > exact_angle)
        # or exactly at it (diff == exact_angle)
        return orb if raw_diff >= 0 else -orb
    else:
        # We're before the exact angle (diff < exact_angle)
        return -orb if raw_diff >= 0 else orb


def signed_angular_difference_v2(
    transit_lon: float,
    natal_lon: float,
    exact_angle: float,
) -> float:
    """Calculate signed angular difference without wrapping.

    This computes f(t) = (transit_lon - natal_lon) - exact_angle
    without wrapping to [0, 360). This allows the function to be
    continuous as transit moves through natal.

    The sign tells us if we're before (negative) or after (positive)
    the exact aspect angle.

    Args:
        transit_lon: Current transiting planet longitude (0-360)
        natal_lon: Natal planet longitude (0-360)
        exact_angle: Exact aspect angle (0, 90, 120, 180, etc.)

    Returns:
        Signed difference in degrees (can be outside [-180, 180])
        Negative = before exact, Positive = after exact
    """
    # Compute the longitudinal difference from natal to transit (allow negatives)
    # This gives a continuous function as transit moves
    signed_diff = (transit_lon - natal_lon) - exact_angle

    return signed_diff


def bisection_solver(
    transit_lon_func: Callable[[float], float],
    natal_lon: float,
    exact_angle: float,
    t0_jd: float,
    t1_jd: float,
    tolerance_degrees: float = 0.005,  # ~18 arcseconds
    max_iterations: int = 50,
) -> TransitTimingResult:
    """Find exact transit timing using bisection on signed angular difference.

    Args:
        transit_lon_func: Function that takes JD and returns transiting planet longitude
        natal_lon: Natal planet longitude (0-360)
        exact_angle: Exact aspect angle for the aspect type
        t0_jd: Start of bracket (Julian Day)
        t1_jd: End of bracket (Julian Day)
        tolerance_degrees: Convergence tolerance in degrees
        max_iterations: Maximum bisection iterations

    Returns:
        TransitTimingResult with exact time and status
    """
    f0 = signed_angular_difference_v2(
        transit_lon_func(t0_jd),
        natal_lon,
        exact_angle,
    )
    f1 = signed_angular_difference_v2(
        transit_lon_func(t1_jd),
        natal_lon,
        exact_angle,
    )

    warnings = []

    # Check for sign change - if no sign change, we might be in a station region
    has_sign_change = (f0 < 0 and f1 > 0) or (f0 > 0 and f1 < 0)

    if not has_sign_change:
        # No sign change - either at a station or the aspect doesn't reach exact
        # Return the best sample with IN_PROGRESS status

        # Sample middle point to find minimum
        tm = (t0_jd + t1_jd) / 2
        f_middle = signed_angular_difference_v2(
            transit_lon_func(tm),
            natal_lon,
            exact_angle,
        )

        # Use the sample with smallest |f| as best
        candidates = [(t0_jd, f0), (tm, f_middle), (t1_jd, f1)]
        best = min(candidates, key=lambda x: abs(x[1]))

        best_jd, best_f = best
        best_lon = transit_lon_func(best_jd)

        # Calculate orb from f value
        # |f| = angular offset from exact aspect
        # But we need actual orb (angular separation from exact)
        diff = abs(best_lon - natal_lon) % 360
        if diff > 180:
            diff = 360 - diff
        min_orb = abs(diff - exact_angle)

        return TransitTimingResult(
            exact_time=None,
            exact_jd=None,
            extrapolated_exact=julian_day_to_datetime(best_jd),
            aspect_status=AspectStatus.IN_PROGRESS,
            min_orb=min_orb,
            orb_range=(min_orb, min_orb + 1.0),
            clipped_at_window_boundary=False,
            warnings=["No sign change in bracket - aspect may be at station or not reaching exact"],
        )

    # Bisection loop
    iterations = 0
    while (t1_jd - t0_jd) > tolerance_degrees / 360.0 * (1 / 24.0) and iterations < max_iterations:
        tm = (t0_jd + t1_jd) / 2
        fm = signed_angular_difference_v2(
            transit_lon_func(tm),
            natal_lon,
            exact_angle,
        )

        if abs(fm) < 0.001:  # Very close to exact
            break

        if fm * f0 < 0:
            t1_jd = tm
            f1 = fm
        else:
            t0_jd = tm
            f0 = fm

        iterations += 1

    # Final midpoint is our best estimate
    exact_jd = (t0_jd + t1_jd) / 2
    exact_lon = transit_lon_func(exact_jd)

    # Calculate orb at exact time
    diff = abs((exact_lon - natal_lon) % 360)
    if diff > 180:
        diff = 360 - diff
    min_orb = abs(diff - exact_angle)

    return TransitTimingResult(
        exact_time=julian_day_to_datetime(exact_jd),
        exact_jd=exact_jd,
        extrapolated_exact=None,
        aspect_status=AspectStatus.EXACT,
        min_orb=min_orb,
        orb_range=(max(0, min_orb - 0.5), min_orb + 0.5),
        clipped_at_window_boundary=False,
        warnings=[],
    )


# =============================================================================
# Integration with scan loop
# =============================================================================


def find_best_bracket(
    samples: list[tuple[datetime, float]],
    natal_lon: float,
    exact_angle: float,
    transit_lon_func: Callable[[float], float],
    window_hours: float = 2.0,
) -> tuple[float, float] | None:
    """Find bracket with sign change around minimum orb sample.

    Args:
        samples: List of (datetime, longitude) samples
        natal_lon: Natal planet longitude
        exact_angle: Exact aspect angle
        transit_lon_func: Function to get transiting longitude at JD
        window_hours: Width of search window around minimum

    Returns:
        (t0_jd, t1_jd) bracket or None if no sign change found
    """
    if len(samples) < 3:
        return None

    # Find sample with minimum |signed_angular_difference|
    def abs_signed_diff(dt: datetime) -> float:
        jd = gregorian_to_julian_day(
            dt.year, dt.month, dt.day + dt.hour / 24 + dt.minute / 1440
        ).jd
        lon = transit_lon_func(jd)
        return abs(signed_angular_difference_v2(lon, natal_lon, exact_angle))

    # Find index of minimum
    min_idx = min(range(len(samples)), key=lambda i: abs_signed_diff(samples[i][0]))

    # Bracket around minimum (use neighbor samples)
    t0_dt, _ = samples[max(0, min_idx - 1)]
    t1_dt, _ = samples[min(len(samples) - 1, min_idx + 1)]

    # Convert to JD
    t0_jd = gregorian_to_julian_day(
        t0_dt.year, t0_dt.month, t0_dt.day + t0_dt.hour / 24 + t0_dt.minute / 1440
    ).jd

    t1_jd = gregorian_to_julian_day(
        t1_dt.year, t1_dt.month, t1_dt.day + t1_dt.hour / 24 + t1_dt.minute / 1440
    ).jd

    # Verify sign change
    f0 = signed_angular_difference_v2(
        transit_lon_func(t0_jd), natal_lon, exact_angle
    )
    f1 = signed_angular_difference_v2(
        transit_lon_func(t1_jd), natal_lon, exact_angle
    )

    has_sign_change = (f0 < 0 and f1 > 0) or (f0 > 0 and f1 < 0)

    if has_sign_change:
        return (t0_jd, t1_jd)
    else:
        # No sign change - try wider bracket
        if min_idx > 1 and min_idx < len(samples) - 2:
            t0_dt, _ = samples[min_idx - 2]
            t1_dt, _ = samples[min_idx + 2]

            t0_jd = gregorian_to_julian_day(
                t0_dt.year, t0_dt.month, t0_dt.day + t0_dt.hour / 24
            ).jd

            t1_jd = gregorian_to_julian_day(
                t1_dt.year, t1_dt.month, t1_dt.day + t1_dt.hour / 24
            ).jd

            f0 = signed_angular_difference_v2(
                transit_lon_func(t0_jd), natal_lon, exact_angle
            )
            f1 = signed_angular_difference_v2(
                transit_lon_func(t1_jd), natal_lon, exact_angle
            )

            if (f0 < 0 and f1 > 0) or (f0 > 0 and f1 < 0):
                return (t0_jd, t1_jd)

    return None


# =============================================================================
# Test helpers
# =============================================================================


def create_linear_ramp_func(
    start_lon: float,
    end_lon: float,
    start_jd: float,
    end_jd: float,
) -> Callable[[float], float]:
    """Create a test function with linear longitudinal movement.

    Args:
        start_lon: Starting longitude
        end_lon: Ending longitude
        start_jd: Start Julian Day
        end_jd: End Julian Day

    Returns:
        Function that returns longitude at given JD
    """
    total_change = (end_lon - start_lon) % 360
    if total_change > 180:
        total_change -= 360

    duration_days = end_jd - start_jd

    def lon_at_jd(jd: float) -> float:
        if jd <= start_jd:
            return start_lon
        if jd >= end_jd:
            return end_lon

        progress = (jd - start_jd) / duration_days
        return (start_lon + total_change * progress) % 360

    return lon_at_jd


def test_bisection_with_linear_ramp():
    """Test bisection with a known linear ramp case."""
    # Setup: transit moving from 10° to 20° over 24 hours
    # Natal at 15°, looking for conjunction (exact_angle = 0)
    start_jd = 2460000.5
    end_jd = start_jd + 1.0

    # Transit moves from 10° to 20°, so it crosses 15° at t = start + 0.5 days
    transit_func = create_linear_ramp_func(10.0, 20.0, start_jd, end_jd)
    natal_lon = 15.0
    exact_angle = 0.0

    result = bisection_solver(
        transit_lon_func=transit_func,
        natal_lon=natal_lon,
        exact_angle=exact_angle,
        t0_jd=start_jd,
        t1_jd=end_jd,
    )

    # Should find exact at 15° (midpoint)
    expected_jd = start_jd + 0.5

    assert result.exact_time is not None, "No exact time found"
    
    actual_jd = result.exact_jd
    assert abs(actual_jd - expected_jd) < 0.01, f"Expected JD {expected_jd}, got {actual_jd}"
