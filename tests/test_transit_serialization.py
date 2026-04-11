"""Tests for transit serialization and deserialization."""

import asyncio
from datetime import datetime
import pytest

from src.astrology_mcp_server.main import (
    _handle_calculate_transits,
    _handle_calculate_natal_chart,
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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

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

        result = asyncio.run(_handle_calculate_transits(arguments))

        # Should handle gracefully even with no planets
        assert len(result) == 1
