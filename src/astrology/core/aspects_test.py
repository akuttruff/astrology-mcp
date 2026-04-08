"""Tests for aspects module."""

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
    # Jupiter at 10° Sagittarius (250.0), Saturn at 10° Gemini (70.0)
    # Trine = 120°

    jupiter_pos = PlanetPosition(
        planet=Planet.JUPITER,
        longitude=ZonalPosition(longitude=250.0, sign_index=9, sign_name="Sagittarius", degree_in_sign=10.0),
        latitude=0.0,
        distance=5.2,
        retrograde=False,
        motion_speed=0.083,
    )

    saturn_pos = PlanetPosition(
        planet=Planet.SATURN,
        longitude=ZonalPosition(longitude=70.0, sign_index=2, sign_name="Gemini", degree_in_sign=10.0),
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


if __name__ == "__main__":
    test_aspect_calculation()
    test_trine_calculation()
    test_conjunction_calculation()
