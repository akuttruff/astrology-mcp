#!/usr/bin/env python3
"""Example usage of the astrology MCP tool."""

from datetime import datetime, timezone

from astrology.charts.chart import calculate_natal_chart
from astrology.core.aspects import get_major_aspects
from astrology.transits.transit import get_current_transits


def main():
    print("=" * 60)
    print("Astrology MCP Tool - Example Usage")
    print("=" * 60)

    # Example 1: Calculate natal chart
    print("\n1. Calculating Natal Chart")
    print("-" * 40)

    birth_datetime = datetime(1990, 6, 15, 14, 30)
    latitude = 40.7128  # New York
    longitude = -74.0060

    chart = calculate_natal_chart(
        birth_datetime=birth_datetime,
        latitude=latitude,
        longitude=longitude,
    )

    print(f"Birth: {birth_datetime}")
    print(f"Location: ({latitude}, {longitude})")
    print("\nPlanetary Positions:")
    for planet, position in chart.planets.items():
        retro = "R" if position.retrograde else ""
        print(f"  {planet.name:10} {position.longitude.sign_name:12} "
              f"{position.longitude.degree_in_sign:5.1f}° {retro}")

    print(f"\nAscendant: {chart.ascendant.sign_name} "
          f"{chart.ascendant.degree_in_sign:.1f}°")
    print(f"MC: {chart.midheaven.sign_name} {chart.midheaven.degree_in_sign:.1f}°")

    # Example 2: Calculate aspects
    print("\n\n2. Major Aspects in Chart")
    print("-" * 40)

    aspects = get_major_aspects(chart.planets)
    for aspect in aspects[:10]:  # Show top 10
        print(f"  {aspect.type.name:12} {aspect.planet1.name:10} - "
              f"{aspect.planet2.name:10} (orb: {aspect.orb:.1f}°)")

    # Example 3: Current transits
    print("\n\n3. Current Transits")
    print("-" * 40)

    current_datetime = datetime.now(timezone.utc)
    transit_report = get_current_transits(chart, current_datetime)

    print(f"Transit Date: {current_datetime}")
    if transit_report.transits:
        for event in transit_report.transits[:5]:
            print(f"  {event.planet.name:10} transiting "
                  f"{event.aspect_type.name.lower()} {event.orb:.1f}°")
    else:
        print("  No significant transits currently active.")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
