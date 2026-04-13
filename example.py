#!/usr/bin/env python3
"""Example usage of the astrology MCP tool.

This example demonstrates both:
1. Direct library usage (for Python scripts)
2. The MCP server pattern with result_id caching (for LLM integration)

For the MCP server pattern, see README.md for how to run the server.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from astrology.charts.chart import calculate_natal_chart
from astrology.core.aspects import get_major_aspects
from astrology.transits.transit import get_current_transits


def direct_library_usage():
    """Example: Direct library usage (no MCP server)."""
    print("=" * 60)
    print("Direct Library Usage")
    print("=" * 60)

    # Calculate natal chart
    birth_datetime = datetime(1984, 5, 10, 20, 44, tzinfo=timezone(timedelta(hours=-7)))
    latitude = 34.02
    longitude = -118.45

    chart = calculate_natal_chart(
        birth_datetime=birth_datetime,
        latitude=latitude,
        longitude=longitude,
    )

    print(f"\nBirth: {birth_datetime}")
    print(f"Location: ({latitude}, {longitude})")
    
    # Show preview (key highlights)
    print("\nPreview:")
    from astrology.core.ephemeris import Planet
    sun_pos = chart.planets.get(Planet.SUN)
    moon_pos = chart.planets.get(Planet.MOON)
    
    if sun_pos:
        print(f"  Sun: {sun_pos.zonal.sign_name} {sun_pos.zonal.degree_in_sign:.1f}°")
    if moon_pos:
        print(f"  Moon: {moon_pos.zonal.sign_name} {moon_pos.zonal.degree_in_sign:.1f}°")
    if chart.ascendant:
        print(f"  Ascendant: {chart.ascendant.sign_name} {chart.ascendant.degree_in_sign:.1f}°")

    # Calculate and show aspects
    print("\nMajor Aspects:")
    aspects = get_major_aspects(chart.planets)
    for aspect in aspects[:5]:
        print(f"  {aspect.type.name:12} {aspect.planet1.name:10} - "
              f"{aspect.planet2.name:10} (orb: {aspect.orb:.1f}°)")

    # Calculate transits
    print("\nTransits:")
    current_dt = datetime.now(timezone.utc)
    transit_report = get_current_transits(chart, current_dt)
    
    for event in transit_report.transits[:5]:
        print(f"  {event.planet.name:10} transiting "
              f"{event.aspect_type.name.lower()} {event.natal_planet.name} "
              f"(orb: {event.orb:.1f}°)")


def mcp_server_with_caching():
    """Example: Using MCP server with result_id caching pattern.
    
    This demonstrates the lazy loading pattern where:
    1. calculate_natal_chart returns {result_id, preview}
    2. Preview contains key data for quick decisions
    3. get_result(result_id) fetches full data when needed
    4. calculate_transits can use natal_chart_id for lean context
    
    Run the server first: `python -m src.astrology_mcp_server.main`
    Then use a client to call these tools.
    """
    print("\n" + "=" * 60)
    print("MCP Server with Caching Pattern")
    print("=" * 60)
    
    print("""
The MCP server implements a lazy loading pattern for large payloads:

FLOW 1: Quick decision with preview (no full data transfer)
------------------------------------------------------------
LLM calls:
  calculate_natal_chart(birth_datetime, lat, lon)
    → { result_id: "nc_a3f9", preview: {sun_sign, moon_sign, rising_sign} }
    
LLM makes quick decision using preview data only.

FLOW 2: Full data when needed
-----------------------------
LLM calls:
  get_result(result_id="nc_a3f9")
    → { full natal chart data with all planets, houses, etc. }
    
LLM reasons over complete data.

FLOW 3: Using result_id for transit calculations
-------------------------------------------------
LLM calls:
  calculate_transits(natal_chart_id="nc_a3f9", current_datetime=...)
    → Transit report (full chart fetched from cache internally)

BENEFITS:
- Preview keeps context lean for simple decisions
- Full data fetched only when truly needed (lazy loading)
- result_id passed between tools keeps context minimal
- Cached results expire after 1 hour (TTL)
""")


def main():
    print("\n" + "=" * 60)
    print("Astrology MCP Tool - Example Usage")
    print("=" * 60)

    # Example 1: Direct library usage
    direct_library_usage()

    # Example 2: MCP server pattern explanation
    mcp_server_with_caching()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
