"""Utility functions for transit report formatting and interpretation."""

from __future__ import annotations

from astrology.core.aspects import AspectType, ASPECT_NAMES
from astrology.transits.transit import TransitEvent


def get_aspect_display_name(aspect_type: AspectType) -> str:
    """Get a user-friendly display name for an aspect type.

    Args:
        aspect_type: The AspectType enum value

    Returns:
        Human-readable aspect name (e.g., "Octile" instead of "Orientation")
    """
    # Use the existing ASPECT_NAMES dict for standard mapping
    return ASPECT_NAMES.get(aspect_type, aspect_type.name.title())


def format_transit_event(event: TransitEvent) -> str:
    """Format a transit event for human-readable reports.

    Args:
        event: The TransitEvent to format

    Returns:
        Formatted string suitable for transit reports
    """
    aspect_name = get_aspect_display_name(event.aspect_type)
    return f"{event.planet.name} transiting {aspect_name} natal position (orb: {event.orb:.2f}°)"


def is_major_aspect(aspect_type: AspectType) -> bool:
    """Check if an aspect is considered 'major' in traditional astrology.

    Major aspects: conjunction, opposition, square, trine, sextile

    Args:
        aspect_type: The AspectType to check

    Returns:
        True if major, False if minor/integer
    """
    major_aspects = {
        AspectType.CONJUNCTION,
        AspectType.OPPOSITION,
        AspectType.SQUARE,
        AspectType.TRINE,
        AspectType.SEXTILE
    }
    return aspect_type in major_aspects


def get_aspect_category(aspect_type: AspectType) -> str:
    """Get the category of an aspect for interpretive purposes.

    Args:
        aspect_type: The AspectType

    Returns:
        Category string: 'major', 'minor', or 'integer'
    """
    if is_major_aspect(aspect_type):
        return "major"
    
    # Minor aspects (often used in modern astrology)
    minor_aspects = {
        AspectType.ORIENTATION,  # Octile - 45°
        AspectType.SEPTILE,      # Septile - ~51.43°
        AspectType.SEMI_SEXTILE, # Semi-Sextile - 30°
        AspectType.SEMI_SQUARE,  # Semi-Square - 45°
        AspectType.SESQUI_SQUARE, # Sesqui-Square - 135°
        AspectType.QUINCUNX,     # Quincunx - 150°
    }
    
    if aspect_type in minor_aspects:
        return "minor"
    
    return "integer"


def get_aspect_interpretation_notes(aspect_type: AspectType) -> str | None:
    """Get interpretive notes for an aspect type.

    Args:
        aspect_type: The AspectType

    Returns:
        Interpretive notes or None if not available
    """
    interpretations = {
        AspectType.ORIENTATION: (
            "Octile (45°) - A minor aspect indicating tension or stimulation. "
            "It creates a need for adjustment and can bring sudden changes or "
            "increased energy in the affected area."
        ),
        AspectType.SEPTILE: (
            "Septile (~51.43°) - A spiritual aspect associated with inspiration, "
            "creativity, and mystical experiences. It's often linked to artistic "
            "talent and intuitive insights."
        ),
        AspectType.QUINCUNX: (
            "Quincunx (150°) - A challenging aspect indicating adjustment or "
            "discomfort. It suggests areas of life that need adaptation and "
            "reconciliation between different needs."
        ),
    }
    
    return interpretations.get(aspect_type)
