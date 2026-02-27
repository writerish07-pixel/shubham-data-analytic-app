"""
Indian Festival Intelligence Engine
Tracks Hindu calendar festivals, marriage seasons, and their sales impact.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple


# Hardcoded festival calendar (Panchang-based, verified dates)
FESTIVAL_CALENDAR: Dict[int, List[Dict]] = {
    2021: [
        {"name": "Pongal",           "date": "2021-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2021-03-11", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2021-03-29", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2021-05-14", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2021-05-13", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2021-08-21", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2021-10-07", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2021-10-15", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2021-11-02", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2021-11-04", "type": "national",   "region": "All India",   "impact_pct": 60},
        {"name": "Bhai Dooj",        "date": "2021-11-06", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Gurpurab",         "date": "2021-11-19", "type": "regional",   "region": "North India", "impact_pct": 15},
    ],
    2022: [
        {"name": "Pongal",           "date": "2022-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2022-03-01", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2022-03-18", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2022-05-03", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2022-05-02", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2022-09-08", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2022-09-26", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2022-10-05", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2022-10-22", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2022-10-24", "type": "national",   "region": "All India",   "impact_pct": 60},
        {"name": "Bhai Dooj",        "date": "2022-10-26", "type": "national",   "region": "All India",   "impact_pct": 20},
    ],
    2023: [
        {"name": "Pongal",           "date": "2023-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2023-02-18", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2023-03-08", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2023-04-22", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2023-04-21", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2023-08-29", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2023-10-15", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2023-10-24", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2023-11-10", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2023-11-12", "type": "national",   "region": "All India",   "impact_pct": 60},
        {"name": "Bhai Dooj",        "date": "2023-11-15", "type": "national",   "region": "All India",   "impact_pct": 20},
    ],
    2024: [
        {"name": "Pongal",           "date": "2024-01-15", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2024-03-08", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2024-03-25", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2024-05-10", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2024-04-10", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2024-09-05", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2024-10-03", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2024-10-12", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2024-10-29", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2024-11-01", "type": "national",   "region": "All India",   "impact_pct": 60},
        {"name": "Bhai Dooj",        "date": "2024-11-03", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Gurpurab",         "date": "2024-11-15", "type": "regional",   "region": "North India", "impact_pct": 15},
    ],
    2025: [
        {"name": "Pongal",           "date": "2025-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2025-02-26", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2025-03-14", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2025-04-30", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2025-03-30", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2025-08-27", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2025-09-22", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2025-10-02", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2025-10-18", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2025-10-20", "type": "national",   "region": "All India",   "impact_pct": 60},
        {"name": "Bhai Dooj",        "date": "2025-10-22", "type": "national",   "region": "All India",   "impact_pct": 20},
    ],
    2026: [
        {"name": "Pongal",           "date": "2026-01-14", "type": "regional",   "region": "South India", "impact_pct": 30},
        {"name": "Maha Shivratri",   "date": "2026-02-15", "type": "auspicious", "region": "All India",   "impact_pct": 10},
        {"name": "Holi",             "date": "2026-03-03", "type": "national",   "region": "All India",   "impact_pct": 15},
        {"name": "Akshaya Tritiya",  "date": "2026-04-20", "type": "auspicious", "region": "All India",   "impact_pct": 25},
        {"name": "Eid ul-Fitr",      "date": "2026-03-20", "type": "national",   "region": "All India",   "impact_pct": 20},
        {"name": "Onam",             "date": "2026-08-17", "type": "regional",   "region": "Kerala",      "impact_pct": 35},
        {"name": "Navratri",         "date": "2026-10-11", "type": "national",   "region": "All India",   "impact_pct": 25},
        {"name": "Dussehra",         "date": "2026-10-20", "type": "national",   "region": "All India",   "impact_pct": 30},
        {"name": "Dhanteras",        "date": "2026-11-06", "type": "national",   "region": "All India",   "impact_pct": 50},
        {"name": "Diwali",           "date": "2026-11-08", "type": "national",   "region": "All India",   "impact_pct": 60},
    ],
}

# Monthly seasonal demand factors for Indian two-wheeler market
# Values > 1.0 indicate above-average demand months
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
    {"season": "Winter",  "months": [11, 12],   "uplift_pct": 25, "colours": ["Pearl White", "Sports Red", "Imperial Blue"], "types": ["scooter", "premium_bike"]},
    {"season": "Spring",  "months": [2, 3, 4, 5], "uplift_pct": 20, "colours": ["Pearl White", "Silver", "Sports Red"],     "types": ["scooter", "standard_bike"]},
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
    year = target_date.year
    upcoming = get_upcoming_festivals(from_date=target_date - timedelta(days=3), days_ahead=30)

    best_multiplier = 1.0
    best_name = None

    for festival in upcoming:
        fdate = festival["date"]
        impact = festival["impact_pct"] / 100.0  # e.g. 0.60 for Diwali
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

    # Build ordered upcoming marriage-season months
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
                "days_away": max(0, days_away),
            }
    return None


def get_all_festivals_flat() -> List[Dict]:
    """Return every festival across all years as a flat list."""
    result = []
    for year, festivals in FESTIVAL_CALENDAR.items():
        for f in festivals:
            result.append({**f, "year": year, "date": _parse_date(f["date"])})
    return sorted(result, key=lambda x: x["date"])
