"""Core calendar and time handling for astrology calculations."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import NamedTuple


class JulianDay(NamedTuple):
    """Represents a Julian Day and related astronomical time data."""
    jd: float  # Julian Day number
    jd_int: float  # Julian Day at noon
    fraction: float  # Fractional part of the day
    jde: float  # Julian Ephemeris Day


class Location(NamedTuple):
    """Geographic location coordinates."""
    latitude: float  # Degrees, positive north
    longitude: float  # Degrees, positive east
    elevation: float = 0.0  # Meters above sea level


class ChartTime(NamedTuple):
    """Complete time information for chart calculation."""
    datetime: datetime
    julian_day: JulianDay
    sidereal_time: float  # Degrees


def gregorian_to_julian_day(year: int, month: int, day: float, hour: float = 12.0) -> JulianDay:
    """Convert Gregorian date to Julian Day.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        day: Day of month (can include decimal for fractional days)
        hour: Hour of day (0-24), defaults to 12 for noon

    Returns:
        JulianDay namedtuple containing JD values

    Example:
        >>> gregorian_to_julian_day(2000, 1, 1, 12)
        JulianDay(jd=2451545.0, ...)
    """
    # Handle hour conversion to fractional day
    if isinstance(day, float):
        day_frac = day - int(day)
        day = int(day)
    else:
        day_frac = 0.0

    # Convert hour to fractional day
    day_frac += hour / 24.0

    # Algorithm from "Astronomical Algorithms" by Jean Meeus
    if month <= 2:
        year -= 1
        month += 12

    a = int(year / 100)
    b = 2 - a + int(a / 4) if year > 1582 else 0

    jd_int = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
    jd = jd_int + day_frac

    # Julian Ephemeris Time correction (approximate)
    # T = (JD - 2451545.0) / 36525
    t = (jd - 2451545.0) / 36525
    delta_t = 2.611 + (0.5831 * t)  # Approximate Delta T in days

    jde = jd + delta_t

    return JulianDay(
        jd=jd,
        jd_int=jd_int,
        fraction=day_frac,
        jde=jde
    )


def julian_day_to_gregorian(jd: float) -> tuple[int, int, float]:
    """Convert Julian Day to Gregorian date.

    Args:
        jd: Julian Day number

    Returns:
        Tuple of (year, month, day_with_fraction)
    """
    z = int(jd + 0.5)
    f = (jd + 0.5) - z

    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - int(alpha / 4)

    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)

    day = b - d - int(30.6001 * e) + f

    if e < 14:
        month = e - 1
    else:
        month = e - 13

    if month > 2:
        year = c - 4716
    else:
        year = c - 4715

    return (year, month, day)


def calculate_sidereal_time(jd: float, longitude: float) -> float:
    """Calculate mean sidereal time at a given Julian Day and longitude.

    Args:
        jd: Julian Day
        longitude: Geographic longitude in degrees (positive east)

    Returns:
        Mean sidereal time in degrees (0-360)
    """
    # Julian centuries from J2000.0
    t = (jd - 2451545.0) / 36525.0

    # Mean sidereal time at Greenwich (Meeus equation 11.4)
    gst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t**2 - 0.0000000258 * t**3

    # Normalize to 0-360
    gst = gst % 360

    # Local sidereal time includes longitude
    lst = gst + longitude

    return lst % 360


def calculate_equation_of_equinoxes(jd: float) -> float:
    """Calculate the equation of equinoxes (nutation in longitude).

    Args:
        jd: Julian Day

    Returns:
        Equation of equinoxes in degrees
    """
    # Julian centuries from J2000.0
    t = (jd - 2451545.0) / 36525.0

    # Mean longitude of the sun
    l = 280.46646 + 36000.76983 * t

    # Mean longitude of the moon
    l_prime = 218.3164591 + 481267.8831 * t

    # Longitude of the ascending node of the moon's orbit
    omega = 125.0445550 - 1934.136261 * t

    # Nutation in longitude (simplified)
    nutation = -0.000319 * math.sin(math.radians(omega)) - 0.000242 * math.sin(math.radians(2 * l))

    return nutation


def calculate_true_sidereal_time(jd: float, longitude: float) -> float:
    """Calculate true sidereal time including nutation.

    Args:
        jd: Julian Day
        longitude: Geographic longitude in degrees

    Returns:
        True sidereal time in degrees
    """
    mean_st = calculate_sidereal_time(jd, longitude)
    eq_eq = calculate_equation_of_equinoxes(jd)

    true_st = mean_st + eq_eq

    return true_st % 360


def to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC.

    Args:
        dt: Input datetime (with or without timezone info)

    Returns:
        Datetime in UTC timezone
    """
    if dt.tzinfo is None:
        # Assume input is already UTC if no timezone
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_chart_time(dt: datetime, location: Location) -> ChartTime:
    """Create a complete ChartTime from datetime and location.

    Args:
        dt: Birth date/time (will be converted to UTC)
        location: Geographic location

    Returns:
        ChartTime with all time calculations
    """
    # Convert to UTC
    dt_utc = to_utc(dt)

    # Calculate Julian Day
    jd = gregorian_to_julian_day(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24
    )

    # Calculate sidereal time
    lst = calculate_true_sidereal_time(jd.jd, location.longitude)

    return ChartTime(
        datetime=dt_utc,
        julian_day=jd,
        sidereal_time=lst
    )


# Constants for common astronomical calculations
J2000_EPOCH = 2451545.0  # Julian Day at 2000-01-01 12:00 UT
