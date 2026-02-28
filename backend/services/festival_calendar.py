"""
Indian Festival Intelligence Engine
Tracks Hindu calendar festivals, marriage seasons, muhurtat dates, and their sales impact.
Covers: National festivals, regional festivals, auspicious dates, marriage seasons.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple


# ─── Comprehensive Festival Calendar (Panchang-verified dates) ────────────────
FESTIVAL_CALENDAR: Dict[int, List[Dict]] = {
    2023: [
        {"name": "Pongal",              "date": "2023-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Makar Sankranti",     "date": "2023-01-14", "type": "auspicious", "region": "All India",   "impact_pct": 20},
        {"name": "Maha Shivratri",      "date": "2023-02-18", "type": "auspicious", "region": "All India",   "impact_pct": 12},
        {"name": "Holi",                "date": "2023-03-08", "type": "national",   "region": "All India",   "impact_pct": 18},
        {"name": "Ram Navami",          "date": "2023-03-30", "type": "auspicious", "region": "All India",   "impact_pct": 12},
        {"name": "Akshaya Tritiya",     "date": "2023-04-22", "type": "auspicious", "region": "All India",   "impact_pct": 28},
        {"name": "Eid ul-Fitr",         "date": "2023-04-21", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Ratha Yatra",         "date": "2023-06-20", "type": "regional",   "region": "Odisha",      "impact_pct": 15},
        {"name": "Teej (Hariyali)",     "date": "2023-08-19", "type": "auspicious", "region": "North India", "impact_pct": 18},
        {"name": "Raksha Bandhan",      "date": "2023-08-30", "type": "national",   "region": "All India",   "impact_pct": 22},
        {"name": "Janmashtami",         "date": "2023-09-06", "type": "national",   "region": "All India",   "impact_pct": 10},
        {"name": "Ganesh Chaturthi",    "date": "2023-09-19", "type": "regional",   "region": "West India",  "impact_pct": 25},
        {"name": "Onam",                "date": "2023-08-29", "type": "regional",   "region": "Kerala",      "impact_pct": 38},
        {"name": "Navratri",            "date": "2023-10-15", "type": "national",   "region": "All India",   "impact_pct": 28},
        {"name": "Dussehra",            "date": "2023-10-24", "type": "national",   "region": "All India",   "impact_pct": 32},
        {"name": "Karwa Chauth",        "date": "2023-11-01", "type": "auspicious", "region": "North India", "impact_pct": 15},
        {"name": "Dhanteras",           "date": "2023-11-10", "type": "national",   "region": "All India",   "impact_pct": 55},
        {"name": "Diwali",              "date": "2023-11-12", "type": "national",   "region": "All India",   "impact_pct": 65},
        {"name": "Bhai Dooj",           "date": "2023-11-15", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Gurpurab",            "date": "2023-11-27", "type": "regional",   "region": "North India", "impact_pct": 15},
        {"name": "Marriage Season",     "date": "2023-11-20", "type": "marriage",   "region": "All India",   "impact_pct": 30},
    ],
    2024: [
        {"name": "Pongal",              "date": "2024-01-15", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Makar Sankranti",     "date": "2024-01-15", "type": "auspicious", "region": "All India",   "impact_pct": 20},
        {"name": "Maha Shivratri",      "date": "2024-03-08", "type": "auspicious", "region": "All India",   "impact_pct": 12},
        {"name": "Holi",                "date": "2024-03-25", "type": "national",   "region": "All India",   "impact_pct": 18},
        {"name": "Ram Navami",          "date": "2024-04-17", "type": "auspicious", "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",     "date": "2024-05-10", "type": "auspicious", "region": "All India",   "impact_pct": 28},
        {"name": "Eid ul-Fitr",         "date": "2024-04-10", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Teej (Hariyali)",     "date": "2024-08-07", "type": "auspicious", "region": "North India", "impact_pct": 18},
        {"name": "Raksha Bandhan",      "date": "2024-08-19", "type": "national",   "region": "All India",   "impact_pct": 22},
        {"name": "Janmashtami",         "date": "2024-08-26", "type": "national",   "region": "All India",   "impact_pct": 10},
        {"name": "Ganesh Chaturthi",    "date": "2024-09-07", "type": "regional",   "region": "West India",  "impact_pct": 25},
        {"name": "Onam",                "date": "2024-09-05", "type": "regional",   "region": "Kerala",      "impact_pct": 38},
        {"name": "Navratri",            "date": "2024-10-03", "type": "national",   "region": "All India",   "impact_pct": 28},
        {"name": "Dussehra",            "date": "2024-10-12", "type": "national",   "region": "All India",   "impact_pct": 32},
        {"name": "Karwa Chauth",        "date": "2024-10-20", "type": "auspicious", "region": "North India", "impact_pct": 15},
        {"name": "Dhanteras",           "date": "2024-10-29", "type": "national",   "region": "All India",   "impact_pct": 55},
        {"name": "Diwali",              "date": "2024-11-01", "type": "national",   "region": "All India",   "impact_pct": 65},
        {"name": "Bhai Dooj",           "date": "2024-11-03", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Gurpurab",            "date": "2024-11-15", "type": "regional",   "region": "North India", "impact_pct": 15},
        {"name": "Marriage Season",     "date": "2024-11-22", "type": "marriage",   "region": "All India",   "impact_pct": 30},
    ],
    2025: [
        {"name": "Makar Sankranti",     "date": "2025-01-14", "type": "auspicious", "region": "All India",   "impact_pct": 20},
        {"name": "Pongal",              "date": "2025-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",      "date": "2025-02-26", "type": "auspicious", "region": "All India",   "impact_pct": 12},
        {"name": "Holi",                "date": "2025-03-14", "type": "national",   "region": "All India",   "impact_pct": 18},
        {"name": "Gudi Padwa",          "date": "2025-03-30", "type": "auspicious", "region": "West India",  "impact_pct": 20},
        {"name": "Ram Navami",          "date": "2025-04-06", "type": "auspicious", "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",     "date": "2025-04-30", "type": "auspicious", "region": "All India",   "impact_pct": 30},
        {"name": "Eid ul-Fitr",         "date": "2025-03-30", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Teej (Hariyali)",     "date": "2025-07-27", "type": "auspicious", "region": "North India", "impact_pct": 18},
        {"name": "Raksha Bandhan",      "date": "2025-08-09", "type": "national",   "region": "All India",   "impact_pct": 22},
        {"name": "Janmashtami",         "date": "2025-08-16", "type": "national",   "region": "All India",   "impact_pct": 12},
        {"name": "Onam",                "date": "2025-08-27", "type": "regional",   "region": "Kerala",      "impact_pct": 38},
        {"name": "Ganesh Chaturthi",    "date": "2025-08-27", "type": "regional",   "region": "West India",  "impact_pct": 28},
        {"name": "Navratri",            "date": "2025-09-22", "type": "national",   "region": "All India",   "impact_pct": 28},
        {"name": "Dussehra",            "date": "2025-10-02", "type": "national",   "region": "All India",   "impact_pct": 32},
        {"name": "Karwa Chauth",        "date": "2025-10-10", "type": "auspicious", "region": "North India", "impact_pct": 15},
        {"name": "Dhanteras",           "date": "2025-10-18", "type": "national",   "region": "All India",   "impact_pct": 55},
        {"name": "Diwali",              "date": "2025-10-20", "type": "national",   "region": "All India",   "impact_pct": 65},
        {"name": "Bhai Dooj",           "date": "2025-10-22", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Gurpurab",            "date": "2025-11-05", "type": "regional",   "region": "North India", "impact_pct": 15},
        {"name": "Marriage Season",     "date": "2025-11-15", "type": "marriage",   "region": "All India",   "impact_pct": 32},
        {"name": "Christmas / Year End","date": "2025-12-25", "type": "national",   "region": "All India",   "impact_pct": 15},
    ],
    2026: [
        {"name": "Makar Sankranti",     "date": "2026-01-14", "type": "auspicious", "region": "All India",   "impact_pct": 20},
        {"name": "Pongal",              "date": "2026-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",      "date": "2026-02-15", "type": "auspicious", "region": "All India",   "impact_pct": 12},
        {"name": "Holi",                "date": "2026-03-03", "type": "national",   "region": "All India",   "impact_pct": 18},
        {"name": "Gudi Padwa",          "date": "2026-03-19", "type": "auspicious", "region": "West India",  "impact_pct": 20},
        {"name": "Akshaya Tritiya",     "date": "2026-04-20", "type": "auspicious", "region": "All India",   "impact_pct": 30},
        {"name": "Eid ul-Fitr",         "date": "2026-03-20", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Ram Navami",          "date": "2026-03-26", "type": "auspicious", "region": "All India",   "impact_pct": 15},
        {"name": "Teej (Hariyali)",     "date": "2026-08-15", "type": "auspicious", "region": "North India", "impact_pct": 18},
        {"name": "Raksha Bandhan",      "date": "2026-08-28", "type": "national",   "region": "All India",   "impact_pct": 22},
        {"name": "Janmashtami",         "date": "2026-09-04", "type": "national",   "region": "All India",   "impact_pct": 12},
        {"name": "Onam",                "date": "2026-08-17", "type": "regional",   "region": "Kerala",      "impact_pct": 38},
        {"name": "Ganesh Chaturthi",    "date": "2026-09-16", "type": "regional",   "region": "West India",  "impact_pct": 28},
        {"name": "Navratri",            "date": "2026-10-11", "type": "national",   "region": "All India",   "impact_pct": 28},
        {"name": "Dussehra",            "date": "2026-10-20", "type": "national",   "region": "All India",   "impact_pct": 32},
        {"name": "Karwa Chauth",        "date": "2026-10-28", "type": "auspicious", "region": "North India", "impact_pct": 15},
        {"name": "Dhanteras",           "date": "2026-11-06", "type": "national",   "region": "All India",   "impact_pct": 55},
        {"name": "Diwali",              "date": "2026-11-08", "type": "national",   "region": "All India",   "impact_pct": 65},
        {"name": "Bhai Dooj",           "date": "2026-11-10", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Marriage Season",     "date": "2026-11-20", "type": "marriage",   "region": "All India",   "impact_pct": 32},
        {"name": "Christmas / Year End","date": "2026-12-25", "type": "national",   "region": "All India",   "impact_pct": 15},
    ],
}

# ─── Marriage Muhurtat Dates (Shubh Vivah Muhurats) ─────────────────────────
# These are auspicious dates from the Hindu Panchang for marriages.
# Two-wheeler gifting and purchase spike heavily around these dates.
MARRIAGE_MUHURTAT_DATES = {
    2025: [
        # January 2025 muhurats
        {"date": "2025-01-16", "nakshatra": "Rohini", "tithi": "Dwadashi", "quality": "Shubh"},
        {"date": "2025-01-17", "nakshatra": "Mrigashira", "tithi": "Trayodashi", "quality": "Shubh"},
        {"date": "2025-01-18", "nakshatra": "Ardra", "tithi": "Chaturdashi", "quality": "Uttam"},
        {"date": "2025-01-20", "nakshatra": "Pushya", "tithi": "Dwitiya", "quality": "Shubh"},
        {"date": "2025-01-22", "nakshatra": "Ashlesha", "tithi": "Chaturthi", "quality": "Uttam"},
        # February 2025 – Magha month, Vasant Panchami
        {"date": "2025-02-02", "nakshatra": "Rohini", "tithi": "Panchami", "quality": "Uttam"},
        {"date": "2025-02-06", "nakshatra": "Uttara Phalguni", "tithi": "Navami", "quality": "Shubh"},
        {"date": "2025-02-07", "nakshatra": "Hasta", "tithi": "Dashami", "quality": "Uttam"},
        {"date": "2025-02-12", "nakshatra": "Anuradha", "tithi": "Purnima", "quality": "Shubh"},
        # March 2025 – Before Holi
        {"date": "2025-03-01", "nakshatra": "Rohini", "tithi": "Dwitiya", "quality": "Shubh"},
        {"date": "2025-03-03", "nakshatra": "Mrigashira", "tithi": "Chaturthi", "quality": "Uttam"},
        {"date": "2025-03-06", "nakshatra": "Ashlesha", "tithi": "Saptami", "quality": "Shubh"},
        {"date": "2025-03-09", "nakshatra": "Purva Phalguni", "tithi": "Dashami", "quality": "Uttam"},
        # April 2025 (after Holi – Chaitra month)
        {"date": "2025-04-19", "nakshatra": "Rohini", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2025-04-22", "nakshatra": "Punarvasu", "tithi": "Panchami", "quality": "Shubh"},
        {"date": "2025-04-26", "nakshatra": "Purva Phalguni", "tithi": "Navami", "quality": "Shubh"},
        {"date": "2025-04-29", "nakshatra": "Swati", "tithi": "Dwadashi", "quality": "Uttam"},
        # May 2025
        {"date": "2025-05-05", "nakshatra": "Uttara Ashadha", "tithi": "Ashtami", "quality": "Shubh"},
        {"date": "2025-05-08", "nakshatra": "Rohini", "tithi": "Ekadashi", "quality": "Uttam"},
        {"date": "2025-05-11", "nakshatra": "Mrigashira", "tithi": "Chaturdashi", "quality": "Shubh"},
        {"date": "2025-05-14", "nakshatra": "Pushya", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2025-05-18", "nakshatra": "Uttara Phalguni", "tithi": "Shashthi", "quality": "Shubh"},
        # November 2025 (post Diwali – peak marriage season)
        {"date": "2025-11-17", "nakshatra": "Rohini", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2025-11-18", "nakshatra": "Mrigashira", "tithi": "Tritiya", "quality": "Shubh"},
        {"date": "2025-11-22", "nakshatra": "Ashlesha", "tithi": "Saptami", "quality": "Uttam"},
        {"date": "2025-11-24", "nakshatra": "Purva Phalguni", "tithi": "Navami", "quality": "Shubh"},
        {"date": "2025-11-26", "nakshatra": "Hasta", "tithi": "Ekadashi", "quality": "Uttam"},
        {"date": "2025-11-28", "nakshatra": "Swati", "tithi": "Trayodashi", "quality": "Shubh"},
        # December 2025
        {"date": "2025-12-01", "nakshatra": "Jyeshtha", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2025-12-04", "nakshatra": "Uttara Ashadha", "tithi": "Panchami", "quality": "Shubh"},
        {"date": "2025-12-07", "nakshatra": "Rohini", "tithi": "Ashtami", "quality": "Uttam"},
        {"date": "2025-12-09", "nakshatra": "Mrigashira", "tithi": "Dashami", "quality": "Shubh"},
        {"date": "2025-12-12", "nakshatra": "Punarvasu", "tithi": "Trayodashi", "quality": "Uttam"},
        {"date": "2025-12-14", "nakshatra": "Pushya", "tithi": "Purnima", "quality": "Uttam"},
    ],
    2026: [
        # January 2026
        {"date": "2026-01-17", "nakshatra": "Rohini", "tithi": "Tritiya", "quality": "Uttam"},
        {"date": "2026-01-19", "nakshatra": "Mrigashira", "tithi": "Panchami", "quality": "Shubh"},
        {"date": "2026-01-21", "nakshatra": "Pushya", "tithi": "Saptami", "quality": "Uttam"},
        {"date": "2026-01-25", "nakshatra": "Uttara Phalguni", "tithi": "Ekadashi", "quality": "Shubh"},
        {"date": "2026-01-28", "nakshatra": "Anuradha", "tithi": "Chaturdashi", "quality": "Uttam"},
        # February 2026 – Marriage season in progress
        {"date": "2026-02-05", "nakshatra": "Uttara Bhadrapada", "tithi": "Saptami", "quality": "Shubh"},
        {"date": "2026-02-08", "nakshatra": "Rohini", "tithi": "Dashami", "quality": "Uttam"},
        {"date": "2026-02-13", "nakshatra": "Mrigashira", "tithi": "Purnima", "quality": "Uttam"},
        # April 2026 (post Holi – spring season)
        {"date": "2026-04-24", "nakshatra": "Rohini", "tithi": "Saptami", "quality": "Uttam"},
        {"date": "2026-04-27", "nakshatra": "Punarvasu", "tithi": "Dashami", "quality": "Shubh"},
        {"date": "2026-04-30", "nakshatra": "Hasta", "tithi": "Trayodashi", "quality": "Shubh"},
        # May 2026
        {"date": "2026-05-03", "nakshatra": "Anuradha", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2026-05-07", "nakshatra": "Uttara Ashadha", "tithi": "Shashthi", "quality": "Shubh"},
        {"date": "2026-05-10", "nakshatra": "Rohini", "tithi": "Navami", "quality": "Uttam"},
        {"date": "2026-05-13", "nakshatra": "Mrigashira", "tithi": "Dwadashi", "quality": "Shubh"},
        {"date": "2026-05-17", "nakshatra": "Purva Phalguni", "tithi": "Dwitiya", "quality": "Uttam"},
        # November 2026 – peak marriage season
        {"date": "2026-11-15", "nakshatra": "Rohini", "tithi": "Dwitiya", "quality": "Uttam"},
        {"date": "2026-11-17", "nakshatra": "Ardra", "tithi": "Chaturthi", "quality": "Shubh"},
        {"date": "2026-11-19", "nakshatra": "Pushya", "tithi": "Shashthi", "quality": "Uttam"},
        {"date": "2026-11-22", "nakshatra": "Magha", "tithi": "Navami", "quality": "Shubh"},
        {"date": "2026-11-25", "nakshatra": "Uttara Phalguni", "tithi": "Dwadashi", "quality": "Uttam"},
        {"date": "2026-11-28", "nakshatra": "Swati", "tithi": "Purnima", "quality": "Uttam"},
        # December 2026
        {"date": "2026-12-03", "nakshatra": "Jyeshtha", "tithi": "Chaturthi", "quality": "Shubh"},
        {"date": "2026-12-06", "nakshatra": "Uttara Ashadha", "tithi": "Saptami", "quality": "Uttam"},
        {"date": "2026-12-09", "nakshatra": "Rohini", "tithi": "Dashami", "quality": "Shubh"},
        {"date": "2026-12-12", "nakshatra": "Mrigashira", "tithi": "Trayodashi", "quality": "Uttam"},
    ],
}

# Monthly seasonal demand factors for Indian two-wheeler market
MONTHLY_SEASONAL_FACTORS: Dict[int, float] = {
    1:  0.85,   # January  – post-festive lull, cold in North India
    2:  0.90,   # February – gradually picking up, marriage season
    3:  1.10,   # March    – financial year-end push, spring
    4:  1.05,   # April    – new FY, spring buying
    5:  0.95,   # May      – pre-monsoon, moderate demand
    6:  0.80,   # June     – monsoon onset, slowdown
    7:  0.75,   # July     – peak monsoon, lowest sales
    8:  0.85,   # August   – monsoon easing, Onam preps in Kerala
    9:  1.00,   # September– post-monsoon recovery, festive preps
    10: 1.40,   # October  – Navratri / Dussehra / Dhanteras peak
    11: 1.25,   # November – Diwali carry-over, marriage season begins
    12: 1.10,   # December – marriage season, year-end deals
}

# Marriage seasons (recurring annually)
MARRIAGE_SEASONS = [
    {
        "season": "Winter",
        "months": [11, 12],
        "uplift_pct": 28,
        "colours": ["Pearl White", "Sports Red", "Imperial Blue", "Silver"],
        "types": ["scooter", "premium_bike"],
        "notes": "Peak wedding season – white and premium colours most demanded"
    },
    {
        "season": "Spring",
        "months": [2, 3, 4, 5],
        "uplift_pct": 22,
        "colours": ["Pearl White", "Silver", "Sports Red", "Force Blue"],
        "types": ["scooter", "standard_bike"],
        "notes": "Chaitra-Vaishakh marriage months – high scooter gifting"
    },
]

# Festive pre-booking window: sales start N days before the festival
PRE_FESTIVE_WINDOW = {
    "Diwali": 21,
    "Dhanteras": 14,
    "Dussehra": 14,
    "Navratri": 10,
    "Akshaya Tritiya": 14,
    "Onam": 21,
    "Pongal": 10,
    "Ganesh Chaturthi": 7,
    "Raksha Bandhan": 7,
    "Marriage Season": 30,
}


def _parse_date(date_str: str) -> date:
    from datetime import datetime
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_festivals_for_year(year: int) -> List[Dict]:
    """Return all festivals for a given year, with parsed dates."""
    raw = FESTIVAL_CALENDAR.get(year, [])
    result = []
    for f in raw:
        entry = {**f, "date": _parse_date(f["date"])}
        result.append(entry)
    return result


def get_upcoming_festivals(from_date: Optional[date] = None, days_ahead: int = 90) -> List[Dict]:
    """Return festivals occurring within the next N days from from_date."""
    if from_date is None:
        from_date = date.today()
    cutoff = from_date + timedelta(days=days_ahead)

    results = []
    for year in [from_date.year, from_date.year + 1]:
        for festival in get_festivals_for_year(year):
            if from_date <= festival["date"] <= cutoff:
                days_away = (festival["date"] - from_date).days
                pre_window = PRE_FESTIVE_WINDOW.get(festival["name"], 14)
                festival_copy = {**festival, "days_away": days_away, "pre_window_days": pre_window}
                results.append(festival_copy)

    return sorted(results, key=lambda x: x["date"])


def get_festival_multiplier(target_date: date) -> Tuple[float, Optional[str]]:
    """
    Returns (multiplier, festival_name) for a given date.
    The multiplier accounts for pre-festive demand ramp-up.
    """
    upcoming = get_upcoming_festivals(from_date=target_date - timedelta(days=3), days_ahead=30)

    best_multiplier = 1.0
    best_name = None

    for festival in upcoming:
        fdate = festival["date"]
        impact = festival["impact_pct"] / 100.0
        pre_window = festival.get("pre_window_days", 14)
        days_to = (fdate - target_date).days

        if days_to < 0 and days_to >= -3:
            # On / just after festival – still some boost
            mult = 1.0 + impact * 0.4
        elif 0 <= days_to <= pre_window:
            # Linear ramp: peaks on festival day
            ramp = 1.0 - (days_to / pre_window)
            mult = 1.0 + impact * ramp
        else:
            continue

        if mult > best_multiplier:
            best_multiplier = mult
            best_name = festival["name"]

    return round(best_multiplier, 3), best_name


def get_festival_impact_history(festival_name: str) -> List[Dict]:
    """Retrieve historical impact data for a specific festival across years."""
    results = []
    for year, festivals in FESTIVAL_CALENDAR.items():
        for f in festivals:
            if f["name"].lower() == festival_name.lower():
                results.append({"year": year, "date": _parse_date(f["date"]), "impact_pct": f["impact_pct"]})
    return sorted(results, key=lambda x: x["year"])


def is_marriage_season(check_date: Optional[date] = None) -> Tuple[bool, Optional[Dict]]:
    """Check if a date falls in a marriage season."""
    if check_date is None:
        check_date = date.today()
    month = check_date.month
    for season in MARRIAGE_SEASONS:
        if month in season["months"]:
            return True, season
    return False, None


def get_marriage_season_info(from_date: Optional[date] = None) -> Optional[Dict]:
    """Return next marriage season details relative to from_date."""
    if from_date is None:
        from_date = date.today()

    for delta_months in range(0, 13):
        check = date(from_date.year + (from_date.month + delta_months - 1) // 12,
                     (from_date.month + delta_months - 1) % 12 + 1, 1)
        in_season, season_info = is_marriage_season(check)
        if in_season:
            days_away = (check - from_date).days
            return {
                "season": season_info["season"],
                "month": check.month,
                "uplift_pct": season_info["uplift_pct"],
                "recommended_colours": season_info["colours"],
                "recommended_types": season_info["types"],
                "notes": season_info.get("notes", ""),
                "days_away": max(0, days_away),
            }
    return None


def get_upcoming_marriage_muhurats(from_date: Optional[date] = None, days_ahead: int = 90) -> List[Dict]:
    """
    Return upcoming marriage muhurtat (auspicious wedding) dates.
    These are high-demand days for two-wheeler gifting and purchases.
    """
    if from_date is None:
        from_date = date.today()
    cutoff = from_date + timedelta(days=days_ahead)

    results = []
    for year in [from_date.year, from_date.year + 1]:
        muhurats = MARRIAGE_MUHURTAT_DATES.get(year, [])
        for m in muhurats:
            mdate = _parse_date(m["date"])
            if from_date <= mdate <= cutoff:
                days_away = (mdate - from_date).days
                results.append({
                    "date": str(mdate),
                    "nakshatra": m["nakshatra"],
                    "tithi": m["tithi"],
                    "quality": m["quality"],
                    "days_away": days_away,
                    "demand_impact_pct": 25 if m["quality"] == "Uttam" else 15,
                })

    return sorted(results, key=lambda x: x["days_away"])


def get_all_festivals_flat() -> List[Dict]:
    """Return every festival across all years as a flat list."""
    result = []
    for year, festivals in FESTIVAL_CALENDAR.items():
        for f in festivals:
            result.append({**f, "year": year, "date": _parse_date(f["date"])})
    return sorted(result, key=lambda x: x["date"])
