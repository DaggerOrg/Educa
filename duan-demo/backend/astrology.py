"""Sun-sign astrology from a birth date.

Real natal-chart astrology also needs birth time + location (for the
ascendant/rising sign), which requires ephemeris data we don't have here.
This computes only the sun sign, which is fully determined by month/day.
"""

ZODIAC_SIGNS = [
    {"sign": "Capricorn", "start": (12, 22), "end": (1, 19), "element": "Earth", "ruling_planet": "Saturn"},
    {"sign": "Aquarius", "start": (1, 20), "end": (2, 18), "element": "Air", "ruling_planet": "Uranus"},
    {"sign": "Pisces", "start": (2, 19), "end": (3, 20), "element": "Water", "ruling_planet": "Neptune"},
    {"sign": "Aries", "start": (3, 21), "end": (4, 19), "element": "Fire", "ruling_planet": "Mars"},
    {"sign": "Taurus", "start": (4, 20), "end": (5, 20), "element": "Earth", "ruling_planet": "Venus"},
    {"sign": "Gemini", "start": (5, 21), "end": (6, 20), "element": "Air", "ruling_planet": "Mercury"},
    {"sign": "Cancer", "start": (6, 21), "end": (7, 22), "element": "Water", "ruling_planet": "Moon"},
    {"sign": "Leo", "start": (7, 23), "end": (8, 22), "element": "Fire", "ruling_planet": "Sun"},
    {"sign": "Virgo", "start": (8, 23), "end": (9, 22), "element": "Earth", "ruling_planet": "Mercury"},
    {"sign": "Libra", "start": (9, 23), "end": (10, 22), "element": "Air", "ruling_planet": "Venus"},
    {"sign": "Scorpio", "start": (10, 23), "end": (11, 21), "element": "Water", "ruling_planet": "Pluto"},
    {"sign": "Sagittarius", "start": (11, 22), "end": (12, 21), "element": "Fire", "ruling_planet": "Jupiter"},
]


def get_sun_sign(month: int, day: int) -> dict:
    for entry in ZODIAC_SIGNS:
        start_month, start_day = entry["start"]
        end_month, end_day = entry["end"]
        if start_month > end_month:  # wraps the new year (Capricorn: Dec 22 - Jan 19)
            in_range = (month == start_month and day >= start_day) or (month == end_month and day <= end_day)
        else:
            in_range = (month == start_month and day >= start_day) or (month == end_month and day <= end_day) or (
                start_month < month < end_month
            )
        if in_range:
            return {"sign": entry["sign"], "element": entry["element"], "ruling_planet": entry["ruling_planet"]}
    raise ValueError(f"Invalid month/day: {month}/{day}")
