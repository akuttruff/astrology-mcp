# Astrology MCP Tasks

## Completed (Current Session)

### Transit Scanning Enhancement
- Implemented `scan_transits` tool for date-range transit scanning
  - Returns exact timing with peak orb windows
  - Significance scoring for filtering important events
  - Optional grouping by 'house', 'planet', or 'theme'
- Added significance weighting based on orb tightness and aspect type
- Implemented structured JSON output with full planet data (name, sign, degree)

### Lunation Scan Implementation
- Implemented `lunation_scan` tool for moon phase detection
  - Real moon phase calculations using ephemeris data
  - Uses synodic month reference (JD 2451550.3 = Jan 6, 2000 18:14 UT)
  - Binary search for precise timing (~1 minute precision)
- Implemented void-of-course period detection based on moon sign changes
  - `find_void_of_course_periods()` function in ephemeris.py
  - Detects when moon changes signs (typically 2-3 days per sign)
- Added `julian_day_to_datetime()` function in calendar.py

### Transit Utility Functions
- Implemented `transit_utils.py` module for transit analysis
  - Aspect name formatting (e.g., "square" → "Square")
  - Major/minor classification
  - Interpretive notes for each aspect type

### Code Changes Made
- **astrology/core/ephemeris.py**: Added moon phase and VoC calculation functions
- **astrology/core/calendar.py**: Added `julian_day_to_datetime()` function
- **src/astrology_mcp_server/tools.py**: Added SCAN_TRANSITS_TOOL and LUNATION_SCAN_TOOL
- **src/astrology_mcp_server/handlers.py**: Added handlers for new tools
- **src/astrology_mcp_server/transit_utils.py**: New module for transit utilities

### Testing
- All 105 existing tests pass
- Integration tests verify correct moon phase dates
- Void-of-course periods correctly detected (14 sign changes in 30 days)
- Transit scanning returns expected results with significance scoring

## Pending

### Documentation Updates
- Update README to reflect all implemented features
- Add examples for transit scanning usage
- Document lunation scan usage

## Notes

### Moon Phase Calculations
- Uses synodic month reference (JD 2451550.3 = Jan 6, 2000 18:14 UT)
- Binary search for precise timing (~1 minute precision)
- Detects New Moon, First Quarter, Full Moon, Last Quarter

### Void-of-Course Detection
- Finds when moon changes signs (typically 2-3 days per sign)
- Important in traditional astrology for determining actionable periods

### Transit Scanning Features
- Significance scoring based on orb tightness and aspect type
- Peak orb window calculation for exact timing
- Optional grouping for reducing result sets
- Full planet data included (name, sign, degree for both transiting and natal)
