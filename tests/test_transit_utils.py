"""Tests for transit utility functions."""

import pytest

from astrology_mcp_server.transit_utils import (
    get_aspect_display_name,
    is_major_aspect,
    get_aspect_category,
    get_aspect_interpretation_notes,
)


class TestGetAspectDisplayName:
    """Tests for get_aspect_display_name function."""

    def test_octile_returns_user_friendly_name(self):
        """Verify Orientation (Octile 45°) returns 'Octile'."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_display_name(AspectType.ORIENTATION)
        assert "Octile" in result

    def test_septile_returns_user_friendly_name(self):
        """Verify Septile (~51.43°) returns 'Septile'."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_display_name(AspectType.SEPTILE)
        assert "Septile" in result

    def test_quincunx_returns_user_friendly_name(self):
        """Verify Quincunx (150°) returns 'Quincunx'."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_display_name(AspectType.QUINCUNX)
        assert "Quincunx" in result

    def test_major_aspects_return_proper_names(self):
        """Verify major aspects return proper names."""
        from astrology.core.aspects import AspectType
        
        major_aspects = [
            (AspectType.CONJUNCTION, "Conjunction"),
            (AspectType.OPPOSITION, "Opposition"),
            (AspectType.SQUARE, "Square"),
            (AspectType.TRINE, "Trine"),
            (AspectType.SEXTILE, "Sextile"),
        ]
        
        for aspect_type, expected_name in major_aspects:
            result = get_aspect_display_name(aspect_type)
            assert expected_name in result

    def test_unknown_aspects_return_title_case(self):
        """Verify unknown aspect types return title case."""
        from astrology.core.aspects import AspectType
        
        # Test with a valid aspect type that has no special handling
        result = get_aspect_display_name(AspectType.SEMI_SEXTILE)
        assert "Semi" in result and "Sextile" in result


class TestIsMajorAspect:
    """Tests for is_major_aspect function."""

    def test_conjunction_is_major(self):
        """Verify conjunction is classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.CONJUNCTION) is True

    def test_opposition_is_major(self):
        """Verify opposition is classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.OPPOSITION) is True

    def test_square_is_major(self):
        """Verify square is classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.SQUARE) is True

    def test_trine_is_major(self):
        """Verify trine is classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.TRINE) is True

    def test_sextile_is_major(self):
        """Verify sextile is classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.SEXTILE) is True

    def test_octile_is_not_major(self):
        """Verify octile (Orientation) is NOT classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.ORIENTATION) is False

    def test_septile_is_not_major(self):
        """Verify septile is NOT classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.SEPTILE) is False

    def test_quincunx_is_not_major(self):
        """Verify quincunx is NOT classified as major."""
        from astrology.core.aspects import AspectType
        
        assert is_major_aspect(AspectType.QUINCUNX) is False


class TestGetAspectCategory:
    """Tests for get_aspect_category function."""

    def test_major_aspects_return_major(self):
        """Verify major aspects return 'major' category."""
        from astrology.core.aspects import AspectType
        
        major_aspects = [
            AspectType.CONJUNCTION,
            AspectType.OPPOSITION,
            AspectType.SQUARE,
            AspectType.TRINE,
            AspectType.SEXTILE,
        ]
        
        for aspect_type in major_aspects:
            result = get_aspect_category(aspect_type)
            assert result == "major"

    def test_octile_returns_minor(self):
        """Verify octile returns 'minor' category."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_category(AspectType.ORIENTATION)
        assert result == "minor"

    def test_septile_returns_minor(self):
        """Verify septile returns 'minor' category."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_category(AspectType.SEPTILE)
        assert result == "minor"

    def test_quincunx_returns_minor(self):
        """Verify quincunx returns 'minor' category."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_category(AspectType.QUINCUNX)
        assert result == "minor"


class TestGetAspectInterpretationNotes:
    """Tests for get_aspect_interpretation_notes function."""

    def test_octile_has_interpretation(self):
        """Verify octile has interpretive notes."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_interpretation_notes(AspectType.ORIENTATION)
        assert result is not None
        assert "Octile" in result or "45" in result

    def test_septile_has_interpretation(self):
        """Verify septile has interpretive notes."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_interpretation_notes(AspectType.SEPTILE)
        assert result is not None
        assert "Septile" in result or "spiritual" in result.lower()

    def test_quincunx_has_interpretation(self):
        """Verify quincunx has interpretive notes."""
        from astrology.core.aspects import AspectType
        
        result = get_aspect_interpretation_notes(AspectType.QUINCUNX)
        assert result is not None
        assert "Quincunx" in result or "adjustment" in result.lower()

    def test_major_aspects_return_none(self):
        """Verify major aspects return None for interpretation notes."""
        from astrology.core.aspects import AspectType
        
        # Major aspects don't have interpretive notes in this implementation
        assert get_aspect_interpretation_notes(AspectType.CONJUNCTION) is None
        assert get_aspect_interpretation_notes(AspectType.OPPOSITION) is None

    def test_unknown_aspects_return_none(self):
        """Verify unknown aspect types return None."""
        from astrology.core.aspects import AspectType
        
        assert get_aspect_interpretation_notes(AspectType.SEMI_SQUARE) is None
