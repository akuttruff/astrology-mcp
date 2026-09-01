# Astrology MCP Tasks

## Completed (Current Session)

### Fix lunar transit tool (calculate moon phases and void-of-course periods)
- Implemented real moon phase calculations using ephemeris data
  - `scan_moon_phases()` function in ephemeris.py
  - Uses synodic month reference (JD 2451550.3 = Jan 6, 2000 18:14 UT)
  - Binary search for precise timing (~1 minute precision)
- Implemented void-of-course period detection based on moon sign changes
  - `find_void_of_course_periods()` function in ephemeris.py  
  - Detects when moon changes signs (typically 2-3 days per sign)
- Added `julian_day_to_datetime()` function in calendar.py
  - Converts Julian Day to Python datetime objects

### Code Changes Made
- **astrology/core/ephemeris.py**: Added 8 new functions for moon phase and VoC calculations
- **astrology/core/calendar.py**: Added `julian_day_to_datetime()` function

### Testing
- All 105 existing tests pass
- Integration tests verify correct moon phase dates
- Void-of-course periods correctly detected (14 sign changes in 30 days)

## Pending
- None - all tasks completed in this session

## Notes
- Moon phase calculations use synodic month reference (JD 2451550.3 = Jan 6, 2000 18:14 UT)
- Void-of-course detection finds when moon changes signs (typically 2-3 days per sign)
- All calculations use binary search for precise timing (~1 minute precision)
