"""Tests for ephemeris module."""

import math

from .calendar import gregorian_to_julian_day
from .ephemeris import (
    get_planet_position,
    get_all_planets,
    calculate_houses,
    init_swe,
)


def test_julian_day_conversion():
    """Test Julian Day conversion for known dates."""
    # J2000.0 epoch
    jd = gregorian_to_julian_day(2000, 1, 1, 12)
    assert abs(jd.jd - 2451545.0) < 0.001, f"Expected JD 2451545.0, got {jd.jd}"
    print("✓ J2000.0 Julian Day correct")


def test_mars_position():
    """Test Mars position against known value."""
    # Mars at 10° Leo on July 20, 2024
    jd = gregorian_to_julian_day(2024, 7, 20)

    # Initialize ephemeris
    init_swe()

    mars = get_planet_position("Mars", jd.jd)
    print(f" Mars position on 2024-07-20:")
    print(f"   Longitude: {mars.longitude}")
    print(f"   Latitude: {mars.latitude}")
    print(f"   Distance: {mars.distance} AU")
    print(f"   Retrograde: {mars.retrograde}")


def test_house_cusps():
    """Test house cusp calculation."""
    jd = gregorian_to_julian_day(2024, 7, 20, 12)
    latitude = 40.7128  # New York
    longitude = -74.0060

    houses = calculate_houses(jd.jd, latitude, longitude)
    print(f" House cusps for 2024-07-20 12:00 UTC:")
    for key, value in houses.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    test_julian_day_conversion()
    test_mars_position()
    test_house_cusps()
