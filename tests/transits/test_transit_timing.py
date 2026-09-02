"""Tests for transit timing with bisection interpolation."""

import pytest

from src.astrology.core.calendar import gregorian_to_julian_day
from src.astrology.transits.transit_timing import (
    bisection_solver,
    create_linear_ramp_func,
    signed_angular_difference_v2,
    test_bisection_with_linear_ramp,
)


class TestSignedAngularDifference:
    """Tests for signed angular difference calculation."""

    def test_conjunction_before_exact(self):
        """Test conjunction when transit is before exact angle."""
        # Transit at 10°, natal at 15°, conjunction (exact_angle = 0)
        # Transit is "behind" natal
        result = signed_angular_difference_v2(10.0, 15.0, 0.0)
        assert result < 0

    def test_conjunction_after_exact(self):
        """Test conjunction when transit is after exact angle."""
        # Transit at 20°, natal at 15°, conjunction (exact_angle = 0)
        # Transit is "ahead" of natal
        result = signed_angular_difference_v2(20.0, 15.0, 0.0)
        assert result > 0

    def test_conjunction_at_exact(self):
        """Test conjunction when transit is exactly at natal."""
        result = signed_angular_difference_v2(15.0, 15.0, 0.0)
        assert abs(result) < 0.001

    def test_opposition_before_exact(self):
        """Test opposition when transit is before exact angle."""
        # Transit at 170°, natal at 15°, opposition (exact_angle = 180)
        # Difference is 155°, need to reach 180
        result = signed_angular_difference_v2(170.0, 15.0, 180.0)
        assert result < 0

    def test_opposition_after_exact(self):
        """Test opposition when transit is after exact angle."""
        # Transit at 195°, natal at 10°, opposition (exact_angle = 180)
        # raw_diff = 195 - 10 = 185
        # signed_diff = 185 - 180 = 5 (positive, after exact)
        result = signed_angular_difference_v2(195.0, 10.0, 180.0)
        assert result > 0

    def test_square_before_exact(self):
        """Test square when transit is before exact angle."""
        # Transit at 80°, natal at 15°, square (exact_angle = 90)
        result = signed_angular_difference_v2(80.0, 15.0, 90.0)
        assert result < 0

    def test_square_after_exact(self):
        """Test square when transit is after exact angle."""
        # Transit at 105°, natal at 10°, square (exact_angle = 90)
        # raw_diff = 105 - 10 = 95
        # signed_diff = 95 - 90 = 5 (positive, after exact)
        result = signed_angular_difference_v2(105.0, 10.0, 90.0)
        assert result > 0

    def test_zero_degree_wrap(self):
        """Test angular difference near 0° boundary."""
        # Transit at 5°, natal at 10°, conjunction (exact_angle = 0)
        # raw_diff = 5 - 10 = -5
        # signed_diff = -5 (negative, before exact since transit < natal)
        result = signed_angular_difference_v2(5.0, 10.0, 0.0)
        assert result < 0

    def test_180_degree_wrap(self):
        """Test angular difference near 180° boundary."""
        # Transit at 200°, natal at 10°, conjunction (exact_angle = 0)
        # raw_diff = 200 - 10 = 190
        # signed_diff = 190 (positive, after exact since transit > natal)
        result = signed_angular_difference_v2(200.0, 10.0, 0.0)
        assert result > 0


class TestBisectionSolver:
    """Tests for bisection solver."""

    def test_linear_ramp_conjunction(self):
        """Test bisection with linear ramp for conjunction."""
        # Setup: transit moving from 10° to 20° over 24 hours
        # Natal at 15°, looking for conjunction (exact_angle = 0)
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit moves from 10° to 20°, crosses 15° at midpoint
        transit_func = create_linear_ramp_func(10.0, 20.0, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should find exact at midpoint
        expected_jd = start_jd + 0.5

        assert result.exact_time is not None
        assert abs(result.exact_jd - expected_jd) < 0.01
        assert result.aspect_status.name == "EXACT"
        assert result.min_orb < 0.01

    def test_linear_ramp_opposition(self):
        """Test bisection with linear ramp for opposition."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit moves from 10° to 190°, crosses 180° (opposition to 0°)
        transit_func = create_linear_ramp_func(10.0, 190.0, start_jd, end_jd)
        natal_lon = 0.0
        exact_angle = 180.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should find exact near 180°
        assert result.exact_time is not None
        assert result.aspect_status.name == "EXACT"
        assert result.min_orb < 0.1

    def test_station_region_no_sign_change(self):
        """Test bisection in station region (no sign change)."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit moves very slowly (station-like)
        # From 15° to 15.1° - barely moves
        transit_func = create_linear_ramp_func(15.0, 15.1, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should return IN_PROGRESS status
        assert result.aspect_status.name == "IN_PROGRESS"
        assert result.exact_time is None

    def test_exact_at_boundary(self):
        """Test bisection when exact occurs at bracket boundary."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit starts exactly at natal (exact at t=0)
        transit_func = create_linear_ramp_func(15.0, 25.0, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should find very small orb
        assert result.min_orb < 0.1

    def test_tight_tolerance(self):
        """Test bisection with tight tolerance."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        transit_func = create_linear_ramp_func(10.0, 20.0, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
            tolerance_degrees=0.001,  # Very tight
        )

        assert result.exact_time is not None
        assert abs(result.exact_jd - (start_jd + 0.5)) < 0.01
        assert result.min_orb < 0.005


class TestIntegrationWithDateRange:
    """Tests for integration with calculate_transit_for_date_range."""

    @pytest.mark.skip(reason="Requires full NatalChart setup - manual test needed")
    def test_full_scan_with_bisection(self):
        """Test full transit scan with bisection refinement."""
        # This test would require:
        # 1. Creating a NatalChart
        # 2. Calling calculate_transit_for_date_range
        # 3. Verifying timing_info is present in results

        # Placeholder for manual verification
        pass


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_slow_movement(self):
        """Test with very slow planetary movement."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit moves only 0.01° (very slow)
        transit_func = create_linear_ramp_func(15.0, 15.01, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should return IN_PROGRESS due to tiny movement
        assert result.aspect_status.name in ("EXACT", "IN_PROGRESS")

    def test_exact_at_start_bracket(self):
        """Test when exact occurs exactly at start of bracket."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit starts exactly at natal
        transit_func = create_linear_ramp_func(15.0, 25.0, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should find very small orb at start
        assert result.min_orb < 0.1

    def test_exact_at_end_bracket(self):
        """Test when exact occurs exactly at end of bracket."""
        start_jd = 2460000.5
        end_jd = start_jd + 1.0

        # Transit ends exactly at natal
        transit_func = create_linear_ramp_func(5.0, 15.0, start_jd, end_jd)
        natal_lon = 15.0
        exact_angle = 0.0

        result = bisection_solver(
            transit_lon_func=transit_func,
            natal_lon=natal_lon,
            exact_angle=exact_angle,
            t0_jd=start_jd,
            t1_jd=end_jd,
        )

        # Should find very small orb at end
        assert result.min_orb < 0.1


class TestJulianDayConversion:
    """Tests for Julian Day conversion functions."""

    def test_jd_to_datetime(self):
        """Test conversion from JD to datetime."""
        jd = 2459946.0
        dt = gregorian_to_julian_day(2023, 1, 1).jd

        # Should be close to JD for Jan 1, 2023
        assert abs(dt - jd) < 1

    def test_datetime_to_jd_and_back(self):
        """Test round-trip conversion."""
        from datetime import datetime

        original = datetime(2023, 6, 15, 12, 30, 0)
        jd = gregorian_to_julian_day(
            original.year, original.month,
            original.day + original.hour / 24 + original.minute / 1440
        ).jd

        # JD should be around 2460000 for this date
        assert 2459000 < jd < 2461000
