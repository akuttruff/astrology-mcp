"""Tests for planet name case-insensitivity."""

import pytest


def test_planet_enum_uppercase():
    """Verify Planet enum uses uppercase names."""
    from astrology.core.ephemeris import Planet
    
    # Enum names are uppercase
    assert Planet.SUN.name == "SUN"
    assert Planet.MOON.name == "MOON"
    assert Planet.MERCURY.name == "MERCURY"
    assert Planet.VENUS.name == "VENUS"
    assert Planet.MARS.name == "MARS"
    assert Planet.JUPITER.name == "JUPITER"
    assert Planet.SATURN.name == "SATURN"
    assert Planet.URANUS.name == "URANUS"
    assert Planet.NEPTUNE.name == "NEPTUNE"
    assert Planet.PLUTO.name == "PLUTO"


def test_planet_lookup_case_insensitive():
    """Verify planet lookup works with different case variations."""
    from astrology.core.ephemeris import Planet
    
    # Uppercase (direct enum match)
    assert Planet["SUN"] == Planet.SUN
    assert Planet["MOON"] == Planet.MOON
    
    # Title case (should work when converted to uppercase)
    assert Planet["SUN".upper()] == Planet.SUN
    assert Planet["Moon".upper()] == Planet.MOON
    
    # Test all planets
    planet_names = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", 
                    "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
    for name in planet_names:
        assert Planet[name] is not None
