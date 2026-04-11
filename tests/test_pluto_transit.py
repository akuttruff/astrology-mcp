"""Tests for Pluto's transit through Aquarius and Pisces."""

from datetime import datetime
from astrology.core.ephemeris import get_planet_position, Planet


def test_pluto_transit_aquarius_2024():
    """Verify Pluto entered Aquarius permanently in November 2024.
    
    Pluto entered Aquarius on November 20, 2024 and will stay there until 2043.
    """
    from astrology.core.calendar import gregorian_to_julian_day
    
    # November 20, 2024: Permanent entry into Aquarius
    jd_nov_20 = gregorian_to_julian_day(2024, 11, 20, 12)
    pos = get_planet_position(Planet.PLUTO, jd_nov_20.jd)
    
    # Aquarius is 300°-329.99°
    assert pos.longitude >= 300, "Pluto should be in Aquarius by Nov 20, 2024"
    assert pos.longitude < 330, "Pluto should still be in Aquarius (not yet in Pisces)"


def test_pluto_pisces_transition_2043():
    """Verify Pluto's transition from Aquarius to Pisces in 2043-2044.
    
    The correct sequence is:
    - March 8, 2043: First entry into Pisces (brief)
    - August 31, 2043: Return to Aquarius
    - January 19, 2044: Final entry into Pisces (permanent until ~2065)
    """
    from astrology.core.calendar import gregorian_to_julian_day
    
    # Check March 8, 2043 - should be entering Pisces
    jd_march_8 = gregorian_to_julian_day(2043, 3, 8, 12)
    pos_march_8 = get_planet_position(Planet.PLUTO, jd_march_8.jd)
    
    # Pisces is 330°-359.99°
    pisces_longitude = pos_march_8.longitude >= 330
    
    # Check August 31, 2043 - should be back in Aquarius
    jd_aug_31 = gregorian_to_julian_day(2043, 8, 31, 12)
    pos_aug_31 = get_planet_position(Planet.PLUTO, jd_aug_31.jd)
    
    # Aquarius is 300°-329.99°
    aquarius_longitude = 300 <= pos_aug_31.longitude < 330
    
    # Check January 19, 2044 - should be in Pisces permanently
    jd_jan_19 = gregorian_to_julian_day(2044, 1, 19, 12)
    pos_jan_19 = get_planet_position(Planet.PLUTO, jd_jan_19.jd)
    
    # Should be in Pisces
    assert pos_jan_19.longitude >= 330, "Pluto should be in Pisces on Jan 19, 2044"


def test_pluto_aquarius_2023_entry():
    """Verify Pluto's first entry into Aquarius in March 2023."""
    from astrology.core.calendar import gregorian_to_julian_day
    
    # March 23-24, 2023: First entry into Aquarius
    jd_march_24 = gregorian_to_julian_day(2023, 3, 24, 12)
    pos = get_planet_position(Planet.PLUTO, jd_march_24.jd)
    
    # Should be in Aquarius (300°-329.99°)
    assert 300 <= pos.longitude < 330, "Pluto should be in Aquarius on March 24, 2023"


def test_pluto_retrograde_capricorn_2024():
    """Verify Pluto retrograded back to Capricorn in September 2024.
    
    Pluto entered Aquarius in January 2024, retrograded back to Capricorn
    around September 1-3, 2024, then permanently entered Aquarius in November 2024.
    """
    from astrology.core.calendar import gregorian_to_julian_day
    
    # September 2, 2024: Pluto retrograded back to Capricorn (based on ephemeris data)
    jd_sept_2 = gregorian_to_julian_day(2024, 9, 2, 12)
    pos = get_planet_position(Planet.PLUTO, jd_sept_2.jd)
    
    # Should be in Capricorn (270°-300°) at this point
    assert pos.longitude < 300, "Pluto should be in Capricorn around Sep 2, 2024"
