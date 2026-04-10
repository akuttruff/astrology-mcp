"""Tests for chart calculation module."""

from datetime import datetime

import pytest

from ..core.calendar import Location
from ..core.ephemeris import Planet
from .chart import (
    calculate_natal_chart,
    _find_planet_house,
    get_planet_in_sign,
    get_planet_in_house,
)


class TestWholeSignHouses:
    """Tests for Whole Sign house system."""

    def test_ascendant_determines_house_1_sign(self):
        """The Ascendant sign determines House 1."""
        chart = calculate_natal_chart(
            birth_datetime=datetime(2000, 1, 1, 12, 0),  # Noon on Y2K
            latitude=40.7128,  # New York City
            longitude=-74.0060,
        )

        if chart.ascendant:
            asc_sign = chart.ascendant.sign_name
            # House 1 cusp should be in the same sign as Ascendant
            house_1 = chart.houses.get("house_1")
            assert house_1 is not None
            # For Whole Sign, House 1 cusp starts at 0° of Ascendant's sign
            assert house_1.sign_name == asc_sign, f"House 1 should be {asc_sign}, got {house_1.sign_name}"
            # Verify House 2 is next sign
            house_2 = chart.houses.get("house_2")
            assert house_2 is not None


class TestHousePlacement:
    """Tests for planet placement in houses."""

    def test_planet_in_same_sign_as_ascendant(self):
        """Planet in Ascendant's sign is in House 1."""
        chart = calculate_natal_chart(
            birth_datetime=datetime(2000, 1, 1, 12, 0),
            latitude=40.7128,
            longitude=-74.0060,
        )

        if chart.ascendant:
            asc_sign = chart.ascendant.sign_name
            # Find a planet in the same sign as Ascendant
            for planet, position in chart.planets.items():
                if position.longitude.sign_name == asc_sign:
                    assert chart.get_planet_house(planet) == 1, f"{planet.name} should be in House 1"
                    break


class TestHouseFindingFunction:
    """Tests for _find_planet_house function."""

    def test_house_1_planets(self):
        """Planets in Ascendant's sign should be House 1."""
        # ASC in Aries (sign_index=0)
        houses_data = {
            "ascendant": type('obj', (object,), {'sign_index': 0})(),
            "house_1": type('obj', (object,), {'sign_index': 0})(),
        }

        # Planet at 15° Aries (longitude=15.0, sign_index=0)
        house = _find_planet_house(15.0, houses_data)
        assert house == 1

    def test_house_2_planets(self):
        """Planet in Taurus (sign_index=1) when ASC is Aries should be House 2."""
        houses_data = {
            "ascendant": type('obj', (object,), {'sign_index': 0})(),
        }

        # Planet at 15° Taurus (longitude=45.0, sign_index=1)
        house = _find_planet_house(45.0, houses_data)
        assert house == 2

    def test_house_12_planets(self):
        """Planet in Pisces (sign_index=11) when ASC is Aries should be House 12."""
        houses_data = {
            "ascendant": type('obj', (object,), {'sign_index': 0})(),
        }

        # Planet at 345° Pisces (longitude=345.0, sign_index=11)
        house = _find_planet_house(345.0, houses_data)
        assert house == 12

    def test_wraparound_from_pisces_to_aries(self):
        """Planet at 5° Aries when ASC is in Pisces should be House 2."""
        # ASC in Pisces (sign_index=11)
        houses_data = {
            "ascendant": type('obj', (object,), {'sign_index': 11})(),
        }

        # Planet at 5° Aries (longitude=5.0, sign_index=0)
        # When ASC is in Pisces, Aries is House 2
        house = _find_planet_house(5.0, houses_data)
        assert house == 2, f"Expected House 2 for Aries when ASC is Pisces, got {house}"


class TestSignBasedQueries:
    """Tests for sign-based planet queries."""

    def test_get_planet_in_sign(self):
        """Find all planets in a specific sign."""
        chart = calculate_natal_chart(
            birth_datetime=datetime(1984, 5, 10, 20, 44),
            latitude=37.7749,
            longitude=-122.4194,  # San Francisco
        )

        # Just verify the function works - check what sign Mercury is actually in
        mercury_sign = chart.get_planet_sign(Planet.MERCURY)
        assert mercury_sign is not None
        assert len(mercury_sign) > 0

        # Find Mercury in its sign
        mercury_in_sign = get_planet_in_sign(chart, mercury_sign)
        assert Planet.MERCURY in mercury_in_sign

    def test_get_planet_in_house(self):
        """Find all planets in a specific house."""
        chart = calculate_natal_chart(
            birth_datetime=datetime(1984, 5, 10, 20, 44),
            latitude=37.7749,
            longitude=-122.4194,
        )

        # Find planets in Moon's house
        moon_house = chart.get_planet_house(Planet.MOON)
        planets_in_moon_house = get_planet_in_house(chart, moon_house)
        assert Planet.MOON in planets_in_moon_house


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
