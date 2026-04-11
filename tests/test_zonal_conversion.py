"""Tests for ZonalPosition conversion and related functionality."""

import pytest

from src.astrology.core.ephemeris import (
    _convert_to_zonal,
    Planet,
    ZonalPosition,
)


class TestConvertToZonal:
    """Tests for _convert_to_zonal function."""

    def test_zero_longitude(self):
        """Test 0° longitude maps to Aries 0°."""
        pos = _convert_to_zonal(0.0, "tropical")
        assert pos.longitude == 0.0
        assert pos.sign_index == 0
        assert pos.sign_name == "Aries"
        assert pos.degree_in_sign == 0.0

    def test_30_degree_longitude(self):
        """Test 30° longitude maps to Taurus 0°."""
        pos = _convert_to_zonal(30.0, "tropical")
        assert pos.longitude == 30.0
        assert pos.sign_index == 1
        assert pos.sign_name == "Taurus"
        assert pos.degree_in_sign == 0.0

    def test_15_degree_longitude(self):
        """Test 15° longitude is 15° into Aries."""
        pos = _convert_to_zonal(15.0, "tropical")
        assert pos.sign_index == 0
        assert pos.sign_name == "Aries"
        assert pos.degree_in_sign == 15.0

    def test_360_degree_wraparound(self):
        """Test 360° wraps to 0°."""
        pos = _convert_to_zonal(360.0, "tropical")
        assert pos.longitude == 0.0
        assert pos.sign_index == 0

    def test_over_360_degree(self):
        """Test longitude over 360° wraps correctly."""
        pos = _convert_to_zonal(450.0, "tropical")
        assert pos.longitude == 90.0
        assert pos.sign_index == 3

    def test_negative_longitude(self):
        """Test negative longitude wraps correctly."""
        pos = _convert_to_zonal(-10.0, "tropical")
        assert pos.longitude == 350.0
        assert pos.sign_index == 11

    def test_pisces_boundary(self):
        """Test longitude at Pisces boundary (359.9°)."""
        pos = _convert_to_zonal(359.0, "tropical")
        assert pos.sign_index == 11
        assert pos.sign_name == "Pisces"
        assert pos.degree_in_sign == 29.0

    def test_sidereal_conversion(self):
        """Test sidereal zodiac with ayanamsa adjustment."""
        pos = _convert_to_zonal(0.0, "sidereal")
        # With Lahiri ayanamsa (~24°), 0° tropical becomes ~336° sidereal (Pisces)
        # The exact value depends on the ayanamsa calculation
        assert pos.sign_index in [10, 11]  # Capricorn or Pisces depending on ayanamsa

    def test_tropical_vs_sidereal_difference(self):
        """Verify tropical and sidereal produce different results."""
        tropical_pos = _convert_to_zonal(45.0, "tropical")
        sidereal_pos = _convert_to_zonal(45.0, "sidereal")

        assert tropical_pos.sign_index != sidereal_pos.sign_index
        assert abs(tropical_pos.longitude - sidereal_pos.longitude) > 20


class TestZonalPositionProperties:
    """Tests for ZonalPosition namedtuple properties."""

    def test_zonal_position_creation(self):
        """Test creating a ZonalPosition directly."""
        pos = ZonalPosition(
            longitude=120.5,
            sign_index=4,
            sign_name="Leo",
            degree_in_sign=0.5
        )
        assert pos.longitude == 120.5
        assert pos.sign_index == 4
        assert pos.sign_name == "Leo"
        assert pos.degree_in_sign == 0.5

    def test_zonal_position_immutability(self):
        """Test that ZonalPosition is immutable."""
        pos = ZonalPosition(
            longitude=0.0,
            sign_index=0,
            sign_name="Aries",
            degree_in_sign=0.0
        )
        with pytest.raises(AttributeError):
            pos.longitude = 10.0


class TestZonalPositionEdgeCases:
    """Tests for edge cases in zonal position handling."""

    def test_exact_sign_boundary(self):
        """Test exact sign boundaries (30°, 60°, etc.)."""
        for i in range(12):
            longitude = i * 30.0
            pos = _convert_to_zonal(longitude, "tropical")
            assert pos.sign_index == i
            assert pos.degree_in_sign == 0.0

    def test_near_boundary_precision(self):
        """Test precision near sign boundaries."""
        # Just before Aries/Taurus boundary
        pos = _convert_to_zonal(29.999, "tropical")
        assert pos.sign_index == 0
        assert abs(pos.degree_in_sign - 29.999) < 0.001

        # Just after Aries/Taurus boundary
        pos = _convert_to_zonal(30.001, "tropical")
        assert pos.sign_index == 1
        assert abs(pos.degree_in_sign - 0.001) < 0.001
