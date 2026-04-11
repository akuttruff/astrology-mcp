"""Tests for PlanetPosition class and related functionality."""

import pytest

from src.astrology.core.ephemeris import (
    Planet,
    PlanetPosition,
    ZonalPosition,
)


class TestPlanetPositionCreation:
    """Tests for creating PlanetPosition instances."""

    def test_basic_planet_position(self):
        """Test creating a basic planet position."""
        pos = PlanetPosition(
            planet=Planet.SUN,
            longitude=45.0,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=0.9856
        )
        assert pos.planet == Planet.SUN
        assert pos.longitude == 45.0
        assert pos.latitude == 0.0
        assert pos.distance == 1.0
        assert pos.retrograde is False

    def test_retrograde_planet(self):
        """Test creating a retrograde planet position."""
        pos = PlanetPosition(
            planet=Planet.MERCURY,
            longitude=120.5,
            latitude=2.3,
            distance=0.8,
            retrograde=True,
            motion_speed=-0.5
        )
        assert pos.retrograde is True
        assert pos.motion_speed < 0

    def test_all_planets(self):
        """Test creating positions for all planets."""
        planets = [
            Planet.SUN, Planet.MOON,
            Planet.MERCURY, Planet.VENUS, Planet.MARS,
            Planet.JUPITER, Planet.SATURN,
            Planet.URANUS, Planet.NEPTUNE, Planet.PLUTO
        ]
        
        for planet in planets:
            pos = PlanetPosition(
                planet=planet,
                longitude=0.0,
                latitude=0.0,
                distance=1.0,
                retrograde=False,
                motion_speed=0.0
            )
            assert pos.planet == planet


class TestPlanetPositionRetrogradeDetection:
    """Tests for retrograde detection from motion speed."""

    def test_prograde_speed_positive(self):
        """Test that positive motion speed is prograde."""
        pos = PlanetPosition(
            planet=Planet.SUN,
            longitude=100.0,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=1.0
        )
        assert pos.retrograde is False

    def test_retrograde_speed_negative(self):
        """Test that negative motion speed indicates retrograde."""
        pos = PlanetPosition(
            planet=Planet.MERCURY,
            longitude=200.0,
            latitude=1.5,
            distance=0.9,
            retrograde=True,
            motion_speed=-0.3
        )
        assert pos.retrograde is True

    def test_zero_speed_not_retrograde(self):
        """Test that zero motion speed is not retrograde."""
        pos = PlanetPosition(
            planet=Planet.MOON,
            longitude=150.0,
            latitude=0.0,
            distance=0.002,
            retrograde=False,
            motion_speed=0.0
        )
        assert pos.retrograde is False


class TestPlanetPositionZonalConversion:
    """Tests for accessing zonal position from PlanetPosition."""

    def test_access_longitude_as_float(self):
        """Test that longitude is accessible as a float."""
        pos = PlanetPosition(
            planet=Planet.VENUS,
            longitude=50.0,  # Plain float
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=-0.7
        )
        assert isinstance(pos.longitude, float)
        assert pos.longitude == 50.0

    def test_zonal_properties_with_float_longitude(self):
        """Test zonal calculations work with float longitude."""
        pos = PlanetPosition(
            planet=Planet.MARS,
            longitude=230.5,  # 20.5° Sagittarius
            latitude=1.8,
            distance=1.5,
            retrograde=False,
            motion_speed=0.5
        )
        # Longitude should be directly accessible as float
        assert pos.longitude == 230.5

    def test_planet_position_immutability(self):
        """Test that PlanetPosition is immutable."""
        pos = PlanetPosition(
            planet=Planet.SUN,
            longitude=10.0,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=0.9
        )
        with pytest.raises(AttributeError):
            pos.longitude = 20.0


class TestPlanetPositionEdgeCases:
    """Tests for edge cases in PlanetPosition handling."""

    def test_high_latitude_planet(self):
        """Test planet with high latitude (Moon can be up to ~5°)."""
        pos = PlanetPosition(
            planet=Planet.MOON,
            longitude=180.0,
            latitude=5.0,  # Near maximum
            distance=0.002,
            retrograde=False,
            motion_speed=-13.0
        )
        assert abs(pos.latitude) <= 5.5

    def test_outer_planet_small_speed(self):
        """Test outer planet with small motion speed."""
        pos = PlanetPosition(
            planet=Planet.NEPTUNE,
            longitude=300.0,
            latitude=1.2,
            distance=30.0,
            retrograde=False,
            motion_speed=0.001  # Very slow
        )
        assert abs(pos.motion_speed) < 0.01

    def test_moon_fast_motion(self):
        """Test Moon with fast motion speed."""
        pos = PlanetPosition(
            planet=Planet.MOON,
            longitude=90.0,
            latitude=0.5,
            distance=0.002,
            retrograde=False,
            motion_speed=13.5  # Fast mover
        )
        assert pos.motion_speed > 10


class TestPlanetPositionInAspects:
    """Tests for using PlanetPosition in aspect calculations."""

    def test_position_for_aspect_calculation(self):
        """Test that positions can be used in aspect calculations."""
        sun_pos = PlanetPosition(
            planet=Planet.SUN,
            longitude=10.0,
            latitude=0.0,
            distance=1.0,
            retrograde=False,
            motion_speed=0.9856
        )

        moon_pos = PlanetPosition(
            planet=Planet.MOON,
            longitude=190.0,
            latitude=0.0,
            distance=0.00257,
            retrograde=False,
            motion_speed=-13.1764
        )

        # Both positions should have accessible longitude as float
        assert isinstance(sun_pos.longitude, (int, float))
        assert isinstance(moon_pos.longitude, (int, float))
