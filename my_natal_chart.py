#!/usr/bin/env python3
"""Your natal chart: May 10th, 1984, 8:44pm, Culver City, CA."""

from datetime import datetime, timezone, timedelta

from astrology.charts.chart import calculate_natal_chart
from astrology.core.aspects import get_major_aspects


def main():
    # Your birth data: May 10th, 1984, 8:44pm, Culver City, CA
    # Note: In 1984, California was on PDT (UTC-7) in May
    birth_datetime = datetime(1984, 5, 10, 20, 44, tzinfo=timezone(timedelta(hours=-7)))
    latitude = 34.0211  # Culver City
    longitude = -118.3965

    print("=" * 70)
    print("YOUR NATAL CHART")
    print("=" * 70)
    print(f"\nBirth: {birth_datetime.strftime('%B %d, %Y at %-I:%M %p %Z')}")
    print(f"Location: Culver City, CA ({latitude:.4f}, {longitude:.4f})")

    # Calculate chart
    chart = calculate_natal_chart(
        birth_datetime=birth_datetime,
        latitude=latitude,
        longitude=longitude,
    )

    # Print planetary positions
    print("\n" + "-" * 70)
    print("PLANETARY POSITIONS")
    print("-" * 70)

    for planet, position in chart.planets.items():
        retro = "R" if position.retrograde else ""
        print(f"{planet.name:10} {position.zonal.sign_name:12} "
              f"{position.zonal.degree_in_sign:5.1f}° {retro}")

    # Print angles
    print("\n" + "-" * 70)
    print("ANGLES")
    print("-" * 70)
    if chart.ascendant:
        print(f"Ascendant: {chart.ascendant.sign_name} "
              f"{chart.ascendant.degree_in_sign:.1f}°")
    if chart.midheaven:
        print(f"MC:        {chart.midheaven.sign_name} "
              f"{chart.midheaven.degree_in_sign:.1f}°")

    # Print house positions
    print("\n" + "-" * 70)
    print("HOUSE POSITIONS")
    print("-" * 70)
    for planet, house in chart.house_positions.items():
        print(f"{planet.name:10} House {house}")

    # Print aspects
    print("\n" + "-" * 70)
    print("MAJOR ASPECTS (orb ≤ 5°)")
    print("-" * 70)

    aspects = get_major_aspects(chart.planets)
    for aspect in aspects:
        if aspect.orb <= 5.0:  # Orb within 5 degrees
            print(f"{aspect.type.name:12} {aspect.planet1.name:10} - "
                  f"{aspect.planet2.name:10} (orb: {aspect.orb:.2f}°)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
