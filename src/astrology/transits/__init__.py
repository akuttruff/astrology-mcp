"""Transit calculations module."""

from .transit import (
    TransitEvent,
    TransitConfiguration,
    TransitReport,
    calculate_single_transit,
    get_current_transits,
    find_major_transit_dates,
    get_transit_summary,
    calculate_transit_for_date_range,
    refine_transit_with_bisection,
    transit_to_dict,
    get_peak_orb_window,
)

from .transit_timing import (
    TransitTimingResult,
    AspectStatus,
    bisection_solver,
)

__all__ = [
    "TransitEvent",
    "TransitConfiguration",
    "TransitReport",
    "calculate_single_transit",
    "get_current_transits",
    "find_major_transit_dates",
    "get_transit_summary",
    "calculate_transit_for_date_range",
    "refine_transit_with_bisection",
    "transit_to_dict",
    "get_peak_orb_window",
    "TransitTimingResult",
    "AspectStatus",
    "bisection_solver",
]
