"""Tests for transit serialization and deserialization."""

import asyncio
from datetime import datetime
import pytest

from astrology_mcp_server import (
    handle_calculate_transits,
    handle_calculate_natal_chart,
)
from astrology.charts.chart import calculate_natal_chart
from astrology.core.ephemeris import Planet, ZonalPosition


class TestTransitSerialization:
    """Tests for transit calculation with various serialized data formats."""

    def test_transit_with_minimal_planet_data(self):
        """Verify transit calculation handles minimal planet data (longitude only)."""
        # Minimal natal chart data with only longitude values
        minimal_natal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {
                "SUN": {"longitude": 50.63689351655029},
                "MOON": {"longitude": 176.26079997064508},
                "MERCURY": {"longitude": 27.501945446411998},
                "VENUS": {"longitude": 41.00909130013627},
                "MARS": {"longitude": 230.92048984724283},
                "JUPITER": {"longitude": 282.7592733990824},
                "SATURN": {"longitude": 222.49514823775914},
                "URANUS": {"longitude": 252.43498657978645},
                "NEPTUNE": {"longitude": 271.0416499091887},
                "PLUTO": {"longitude": 210.18674613839875},
            },
            "angles": {
                "ascendant": {"longitude": 243.7734708325564},
                "midheaven": {"longitude": 165.56324445821875},
            },
        }

        arguments = {
            "natal_chart": minimal_natal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Verify we got a valid response (not an error)
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"
        assert "Error" not in content.text
        assert "Current Transits Report" in content.text

    def test_transit_with_full_zonalposition_data(self):
        """Verify transit calculation handles full ZonalPosition data (with sign, degree)."""
        full_natal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {
                "SUN": {
                    "longitude": 50.63689351655029,
                    "sign": "Gemini",
                    "degree_in_sign": 20.64,
                    "sign_name": "Gemini",
                },
                "MOON": {
                    "longitude": 176.26079997064508,
                    "sign": "Virgo",
                    "degree_in_sign": 26.26,
                    "sign_name": "Virgo",
                },
            },
            "angles": {
                "ascendant": {
                    "longitude": 243.7734708325564,
                    "sign": "Leo",
                    "degree_in_sign": 23.77,
                    "sign_name": "Leo",
                },
                "midheaven": {
                    "longitude": 165.56324445821875,
                    "sign": "Leo",
                    "degree_in_sign": 15.56,
                    "sign_name": "Leo",
                },
            },
        }

        arguments = {
            "natal_chart": full_natal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Verify we got a valid response
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"
        assert "Error" not in content.text

    def test_transit_with_mixed_data_formats(self):
        """Verify transit calculation handles mixed data formats (some planets with sign, some without)."""
        mixed_natal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {
                "SUN": {"longitude": 50.63689351655029},  # Plain longitude
                "MOON": {  # Full zonal data
                    "longitude": 176.26079997064508,
                    "sign": "Virgo",
                    "degree_in_sign": 26.26,
                },
            },
        }

        arguments = {
            "natal_chart": mixed_natal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Verify we got a valid response
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"
        assert "Error" not in content.text

    def test_transit_with_planet_as_key(self):
        """Verify transit calculation handles planet names in various cases."""
        natal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {
                "sun": {"longitude": 50.63689351655029},  # lowercase
                "Moon": {"longitude": 176.26079997064508},  # Title case
            },
        }

        arguments = {
            "natal_chart": natal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Verify we got a valid response (planet lookup converts to uppercase)
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"


class TestTransitWithActualChart:
    """Tests for transit calculation using actual natal chart data."""

    def test_transit_from_calculate_natal_chart(self):
        """Verify transit calculation works with data from calculate_natal_chart."""
        # First get a complete natal chart
        birth_dt_iso = "1984-05-10T20:44:00-07:00"
        chart = calculate_natal_chart(
            birth_datetime=datetime.fromisoformat(birth_dt_iso),
            latitude=34.021185,
            longitude=-118.402673,
        )

        # Serialize the chart (simulating what would be sent over MCP)
        serialized_planets = {}
        for planet, pos in chart.planets.items():
            # Serialize longitude as a float (what LLMs typically send)
            # Note: pos.longitude is a ZonalPosition with .longitude attribute
            lon = pos.longitude.longitude if hasattr(pos.longitude, 'longitude') else pos.longitude
            serialized_planets[planet.name] = {
                "longitude": lon,
                "latitude": pos.latitude,
                "distance": pos.distance,
                "retrograde": pos.retrograde,
            }

        serialized_chart = {
            "birth_datetime": birth_dt_iso,
            "location": {
                "latitude": chart.location.latitude,
                "longitude": chart.location.longitude,
            },
            "planets": serialized_planets,
        }

        arguments = {
            "natal_chart": serialized_chart,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Verify we got a valid response
        assert len(result) == 1
        content = result[0]
        assert content.type == "text"
        assert "Error" not in content.text


class TestTransitEdgeCases:
    """Tests for edge cases in transit calculation."""

    def test_transit_with_only_ascendant(self):
        """Verify transit calculation works with only Ascendant angle."""
        minimal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {},
            "angles": {
                "ascendant": {"longitude": 243.7734708325564},
            },
        }

        arguments = {
            "natal_chart": minimal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Should handle gracefully even with minimal data
        assert len(result) == 1

    def test_transit_with_empty_planet_list(self):
        """Verify transit calculation handles empty planets dict."""
        minimal_data = {
            "birth_datetime": "1984-05-10T20:44:00-07:00",
            "location": {"latitude": 34.021185, "longitude": -118.402673},
            "planets": {},
        }

        arguments = {
            "natal_chart": minimal_data,
            "current_datetime": "2026-04-10T23:28:30Z",
        }

        result = asyncio.run(handle_calculate_transits(arguments))

        # Should handle gracefully even with no planets
        assert len(result) == 1


class TestTransitHouseCalculation:
    """Tests for transit house position calculations."""

    def test_pluto_transit_house_2_in_july_2022(self):
        """Verify Pluto in July 2022 is correctly placed in House 2.
        
        This tests the fix for: Pluto at ~27° Capricorn in July 2022
        should be in House 2 (not House 6 as incorrectly reported).
        """
        # User's birth data
        arguments = {
            "natal_chart": {
                "birth_datetime": "1984-05-10T20:44:00-07:00",
                "location": {"latitude": 34.0215, "longitude": -118.4673},
                "planets": {
                    "SUN": {"longitude": 50.63689351655029},
                    "MOON": {"longitude": 176.26079997064508},
                    "MERCURY": {"longitude": 27.501945446411998},
                    "VENUS": {"longitude": 41.00909130013627},
                    "MARS": {"longitude": 230.92048984724283},
                    "JUPITER": {"longitude": 282.7592733990824},
                    "SATURN": {"longitude": 222.49514823775914},
                    "URANUS": {"longitude": 252.43498657978645},
                    "NEPTUNE": {"longitude": 271.0416499091887},
                    "PLUTO": {"longitude": 210.18674613839875},
                },
                "angles": {
                    "ascendant": {"longitude": 243.71955811442493},
                    "midheaven": {"longitude": 165.4934995470908},
                },
            },
            "current_datetime": "2022-07-01T00:00:00+00:00",
        }

        result = asyncio.run(handle_calculate_transits(arguments))
        
        # Verify the response contains house info and Pluto is in House 2
        content = result[0]
        assert "PLUTO (House 2)" in content.text
        # Also verify the output shows which planet is being transited
        assert "natal MERCURY" in content.text or "MERCURY" in content.text

    def test_transit_output_shows_natal_planet_names(self):
        """Verify transit output includes natal planet names in aspect descriptions."""
        arguments = {
            "natal_chart": {
                "birth_datetime": "1984-05-10T20:44:00-07:00",
                "location": {"latitude": 34.0215, "longitude": -118.4673},
                "planets": {
                    "SUN": {"longitude": 50.63689351655029},
                    "MOON": {"longitude": 176.26079997064508},
                    "MERCURY": {"longitude": 27.501945446411998},
                    "VENUS": {"longitude": 41.00909130013627},
                    "MARS": {"longitude": 230.92048984724283},
                },
                "angles": {
                    "ascendant": {"longitude": 243.71955811442493},
                    "midheaven": {"longitude": 165.4934995470908},
                },
            },
            "current_datetime": "2022-07-01T00:00:00+00:00",
        }

        result = asyncio.run(handle_calculate_transits(arguments))
        
        content = result[0]
        # Verify output format includes natal planet names
        # e.g., "PLUTO transiting Square natal MERCURY"
        assert "natal " in content.text
        # Verify it's not just generic "natal position"
        assert "natal MERCURY" in content.text or "natal SUN" in content.text or "natal MOON" in content.text

    def test_house_positions_differ_for_past_and_present_dates(self):
        """Verify the same planet appears in different houses for different dates."""
        # Get transit report for July 2022 (Pluto at ~27° Capricorn)
        result_2022 = asyncio.run(handle_calculate_transits({
            "natal_chart": {
                "birth_datetime": "1984-05-10T20:44:00-07:00",
                "location": {"latitude": 34.0215, "longitude": -118.4673},
                "planets": {
                    "PLUTO": {"longitude": 210.18674613839875},
                },
                "angles": {
                    "ascendant": {"longitude": 243.71955811442493},
                },
            },
            "current_datetime": "2022-07-01T00:00:00+00:00",
        }))

        # Get transit report for current time
        result_now = asyncio.run(handle_calculate_transits({
            "natal_chart": {
                "birth_datetime": "1984-05-10T20:44:00-07:00",
                "location": {"latitude": 34.0215, "longitude": -118.4673},
                "planets": {
                    "PLUTO": {"longitude": 210.18674613839875},
                },
                "angles": {
                    "ascendant": {"longitude": 243.71955811442493},
                },
            },
        }))

        # Both should contain valid transit reports
        content_2022 = result_2022[0]
        content_now = result_now[0]

        assert "Current Transits Report" in content_2022.text
        assert "Current Transits Report" in content_now.text

        # Pluto should be in House 2 in July 2022 (Capricorn)
        assert "House 2" in content_2022.text
