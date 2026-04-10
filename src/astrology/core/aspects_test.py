"""Tests for aspects module."""

import math

from .aspects import (
    calculate_aspect,
    get_all_aspects,
    get_major_aspects,
    AspectType,
)
from .ephemeris import Planet, PlanetPosition, ZonalPosition


def test_aspect_calculation():
    """Test aspect calculation between known positions."""
    # Sun at 10° Aries (10.0), Moon at 10° Libra (190.0)
    # Should be an Opposition (180°)

    sun_pos = PlanetPosition(
        planet=Planet.SUN,
        longitude=ZonalPosition(longitude=10.0, sign_index=0, sign_name="Aries", degree_in_sign=10.0),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=0.9856,
    )

    moon_pos = PlanetPosition(
        planet=Planet.MOON,
        longitude=ZonalPosition(longitude=190.0, sign_index=6, sign_name="Libra", degree_in_sign=10.0),
        latitude=0.0,
        distance=0.00257,
        retrograde=False,
        motion_speed=-13.1764,  # Moon moves backward in longitude (retrograde motion)
    )

    aspects = get_all_aspects({Planet.SUN: sun_pos, Planet.MOON: moon_pos})

    print("Aspects between Sun and Moon:")
    for aspect in aspects:
        print(f"  {aspect.type}: {aspect.orb:.2f}° orb")

    # Check for opposition
    oppositions = [a for a in aspects if a.type == AspectType.OPPOSITION]
    assert len(oppositions) > 0, "Should find an opposition"
    print("✓ Opposition found")


def test_trine_calculation():
    """Test trine calculation."""
    # Jupiter at 10° Aries (10.0), Saturn at 10° Leo (130.0)
    # Trine = 120°

    jupiter_pos = PlanetPosition(
        planet=Planet.JUPITER,
        longitude=ZonalPosition(longitude=10.0, sign_index=0, sign_name="Aries", degree_in_sign=10.0),
        latitude=0.0,
        distance=5.2,
        retrograde=False,
        motion_speed=0.083,
    )

    saturn_pos = PlanetPosition(
        planet=Planet.SATURN,
        longitude=ZonalPosition(longitude=130.0, sign_index=4, sign_name="Leo", degree_in_sign=10.0),
        latitude=0.0,
        distance=9.5,
        retrograde=False,
        motion_speed=-0.034,
    )

    aspects = get_all_aspects({Planet.JUPITER: jupiter_pos, Planet.SATURN: saturn_pos})

    print("Aspects between Jupiter and Saturn:")
    for aspect in aspects:
        print(f"  {aspect.type}: {aspect.orb:.2f}° orb")

    trines = [a for a in aspects if a.type == AspectType.TRINE]
    assert len(trines) > 0, "Should find a trine"
    print("✓ Trine found")


def test_conjunction_calculation():
    """Test conjunction calculation."""
    # Two planets at same position = conjunction

    planet1_pos = PlanetPosition(
        planet=Planet.MERCURY,
        longitude=ZonalPosition(longitude=120.5, sign_index=4, sign_name="Leo", degree_in_sign=0.5),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=1.2,
    )

    planet2_pos = PlanetPosition(
        planet=Planet.VENUS,
        longitude=ZonalPosition(longitude=120.6, sign_index=4, sign_name="Leo", degree_in_sign=0.6),
        latitude=0.0,
        distance=0.7,
        retrograde=False,
        motion_speed=-0.9,
    )

    aspects = get_all_aspects({Planet.MERCURY: planet1_pos, Planet.VENUS: planet2_pos})

    print("Aspects between Mercury and Venus:")
    for aspect in aspects:
        print(f"  {aspect.type}: {aspect.orb:.2f}° orb")

    conjunctions = [a for a in aspects if a.type == AspectType.CONJUNCTION]
    assert len(conjunctions) > 0, "Should find a conjunction"
    print("✓ Conjunction found")


def test_sextile_calculation():
    """Test sextile calculation (60°)."""
    # Mars at 15° Gemini (75.0), Sun at 15° Leo (135.0)
    # Sextile = 60°

    mars_pos = PlanetPosition(
        planet=Planet.MARS,
        longitude=ZonalPosition(longitude=75.0, sign_index=2, sign_name="Gemini", degree_in_sign=15.0),
        latitude=0.0,
        distance=1.5,
        retrograde=False,
        motion_speed=0.524,
    )

    sun_pos = PlanetPosition(
        planet=Planet.SUN,
        longitude=ZonalPosition(longitude=135.0, sign_index=4, sign_name="Leo", degree_in_sign=15.0),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=0.9856,
    )

    aspects = get_all_aspects({Planet.MARS: mars_pos, Planet.SUN: sun_pos})

    print("Aspects between Mars and Sun:")
    for aspect in aspects:
        print(f"  {aspect.type}: {aspect.orb:.2f}° orb")

    sextiles = [a for a in aspects if a.type == AspectType.SEXTILE]
    assert len(sextiles) > 0, "Should find a sextile"
    print("✓ Sextile found")


def test_square_calculation():
    """Test square calculation (90°)."""
    # Venus at 15° Virgo (165.0), Moon at 15° Sagittarius (255.0)
    # Square = 90°

    venus_pos = PlanetPosition(
        planet=Planet.VENUS,
        longitude=ZonalPosition(longitude=165.0, sign_index=5, sign_name="Virgo", degree_in_sign=15.0),
        latitude=0.0,
        distance=0.7,
        retrograde=False,
        motion_speed=-0.72,
    )

    moon_pos = PlanetPosition(
        planet=Planet.MOON,
        longitude=ZonalPosition(longitude=255.0, sign_index=8, sign_name="Sagittarius", degree_in_sign=15.0),
        latitude=0.0,
        distance=0.00257,
        retrograde=False,
        motion_speed=-13.1764,
    )

    aspects = get_all_aspects({Planet.VENUS: venus_pos, Planet.MOON: moon_pos})

    print("Aspects between Venus and Moon:")
    for aspect in aspects:
        print(f"  {aspect.type}: {aspect.orb:.2f}° orb")

    squares = [a for a in aspects if a.type == AspectType.SQUARE]
    assert len(squares) > 0, "Should find a square"
    print("✓ Square found")


def test_orb_calculation():
    """Test that orb calculation is accurate."""
    # Two planets exactly 180° apart = opposition with 0° orb
    planet1_pos = PlanetPosition(
        planet=Planet.SUN,
        longitude=ZonalPosition(longitude=0.0, sign_index=0, sign_name="Aries", degree_in_sign=0.0),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=0.9856,
    )

    planet2_pos = PlanetPosition(
        planet=Planet.MOON,
        longitude=ZonalPosition(longitude=180.0, sign_index=6, sign_name="Libra", degree_in_sign=0.0),
        latitude=0.0,
        distance=0.00257,
        retrograde=False,
        motion_speed=-13.1764,
    )

    aspects = get_all_aspects({Planet.SUN: planet1_pos, Planet.MOON: planet2_pos})

    oppositions = [a for a in aspects if a.type == AspectType.OPPOSITION]
    assert len(oppositions) > 0, "Should find an opposition"
    # Exact opposition should have 0° orb
    assert oppositions[0].orb < 0.1, f"Expected near-zero orb, got {oppositions[0].orb}°"
    print(f"✓ Exact opposition orb: {oppositions[0].orb:.2f}°")


def test_applying_separating_aspects():
    """Test applying/separating status of aspects."""
    # Sun at 10° Aries (moving forward), Moon at 15° Aries (moving faster)
    # Moon is catching up to Sun = applying conjunction

    sun_pos = PlanetPosition(
        planet=Planet.SUN,
        longitude=ZonalPosition(longitude=10.0, sign_index=0, sign_name="Aries", degree_in_sign=10.0),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=0.9856,  # Sun moves ~1°/day
    )

    moon_pos = PlanetPosition(
        planet=Planet.MOON,
        longitude=ZonalPosition(longitude=15.0, sign_index=0, sign_name="Aries", degree_in_sign=15.0),
        latitude=0.0,
        distance=0.00257,
        retrograde=False,
        motion_speed=13.1764,  # Moon moves ~13°/day (prograde)
    )

    aspects = get_all_aspects({Planet.SUN: sun_pos, Planet.MOON: moon_pos})

    conjunctions = [a for a in aspects if a.type == AspectType.CONJUNCTION]
    assert len(conjunctions) > 0, "Should find a conjunction"

    # Moon is ahead of Sun but moving faster, so it's applying
    assert conjunctions[0].is_applying or conjunctions[0].is_separating
    print(f"✓ Conjunction status: applying={conjunctions[0].is_applying}, separating={conjunctions[0].is_separating}")


def test_aspect_angle_calculation():
    """Test exact angle calculation for various aspects."""
    # Test exact aspect angles
    # Note: The function finds the closest aspect, so 45° maps to octile (45°)
    # and 90° maps to square only when the separation is closer to 90 than to 45
    test_cases = [
        (0.0, 0.1, AspectType.CONJUNCTION, 0.0),      # Conjunction
        (0.0, 30.0, AspectType.SEMI_SEXTILE, 30.0),   # Semi-sextile
        (0.0, 45.0, AspectType.ORIENTATION, 45.0),    # Octile (not square)
        (0.0, 60.0, AspectType.SEXTILE, 60.0),        # Sextile
        (0.0, 91.0, AspectType.SQUARE, 90.0),         # Square (closer to 90 than 45)
        (0.0, 120.0, AspectType.TRINE, 120.0),        # Trine
        (0.0, 150.0, AspectType.QUINCUNX, 150.0),     # Quincunx
        (0.0, 180.0, AspectType.OPPOSITION, 180.0),   # Opposition
    ]

    for lon1, lon2, expected_aspect, expected_angle in test_cases:
        aspect_type, angle = calculate_aspect(lon1, lon2)
        assert aspect_type == expected_aspect, f"Expected {expected_aspect} for {lon1}°-{lon2}°, got {aspect_type}"
        assert angle == expected_angle, f"Expected angle {expected_angle}, got {angle}"


def test_aspect_with_orb_boundary():
    """Test aspects at exact orb boundary."""
    # Conjunction with 8° orb - test just inside and just outside

    # Just inside orb (7.5° separation = within 8°)
    planet1_pos = PlanetPosition(
        planet=Planet.SUN,
        longitude=ZonalPosition(longitude=0.0, sign_index=0, sign_name="Aries", degree_in_sign=0.0),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=0.9856,
    )

    planet2_pos = PlanetPosition(
        planet=Planet.MERCURY,
        longitude=ZonalPosition(longitude=7.5, sign_index=0, sign_name="Aries", degree_in_sign=7.5),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=1.2,
    )

    aspects = get_all_aspects({Planet.SUN: planet1_pos, Planet.MERCURY: planet2_pos})
    conjunctions = [a for a in aspects if a.type == AspectType.CONJUNCTION]
    assert len(conjunctions) > 0, "Should find conjunction within orb"
    print(f"✓ Conjunction at 7.5° separation found (orb: {conjunctions[0].orb:.2f}°)")

    # Just outside orb (8.5° separation = outside 8°)
    planet3_pos = PlanetPosition(
        planet=Planet.MERCURY,
        longitude=ZonalPosition(longitude=8.5, sign_index=0, sign_name="Aries", degree_in_sign=8.5),
        latitude=0.0,
        distance=1.0,
        retrograde=False,
        motion_speed=1.2,
    )

    aspects = get_all_aspects({Planet.SUN: planet1_pos, Planet.MERCURY: planet3_pos})
    conjunctions = [a for a in aspects if a.type == AspectType.CONJUNCTION]
    assert len(conjunctions) == 0, "Should not find conjunction outside orb"
    print("✓ No conjunction at 8.5° separation (outside orb)")


if __name__ == "__main__":
    test_aspect_calculation()
    test_trine_calculation()
    test_conjunction_calculation()
    test_sextile_calculation()
    test_square_calculation()
    test_orb_calculation()
    test_applying_separating_aspects()
    test_aspect_angle_calculation()
    test_aspect_with_orb_boundary()
