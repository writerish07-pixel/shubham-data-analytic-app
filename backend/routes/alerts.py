from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List, Dict

from database import get_db
from services.festival_calendar import get_upcoming_festivals, get_marriage_season_info, is_marriage_season
from services.sales_analytics import get_sku_performance

router = APIRouter()


def _generate_alerts(db: Session) -> List[Dict]:
    """Dynamically generate alerts based on current data and calendar."""
    alerts = []
    today = date.today()
    alert_id = 1

    # 1. Festival proximity alerts
    upcoming = get_upcoming_festivals(days_ahead=45)
    for festival in upcoming:
        days = festival["days_away"]
        if days <= 21:
            priority = "high" if days <= 7 else "medium"
            alerts.append({
                "id": alert_id,
                "alert_type": "festival_approaching",
                "priority": priority,
                "title": f"{festival['name']} in {days} days!",
                "message": (
                    f"{festival['name']} is {days} days away. Expected demand uplift: "
                    f"+{festival['impact_pct']}%. Ensure adequate stock is dispatched now "
                    f"to cover the {festival.get('pre_window_days', 14)}-day pre-festival buying window."
                ),
                "related_festival": festival["name"],
                "action_required": True,
                "is_dismissed": False,
                "created_at": str(today),
            })
            alert_id += 1

    # 2. Marriage season alert
    in_season, season_info = is_marriage_season()
    if in_season and season_info:
        alerts.append({
            "id": alert_id,
            "alert_type": "marriage_season",
            "priority": "medium",
            "title": f"Marriage Season Active – {season_info['season']} Season",
            "message": (
                f"Wedding season is currently active. Expect +{season_info['uplift_pct']}% demand uplift "
                f"for scooters and premium bikes. High-demand colours: {', '.join(season_info['colours'][:3])}."
            ),
            "related_festival": "Marriage Season",
            "action_required": True,
            "is_dismissed": False,
            "created_at": str(today),
        })
        alert_id += 1
    else:
        next_season = get_marriage_season_info()
        if next_season and next_season["days_away"] <= 30:
            alerts.append({
                "id": alert_id,
                "alert_type": "marriage_season_approaching",
                "priority": "medium",
                "title": f"Marriage Season Approaching ({next_season['days_away']} days)",
                "message": (
                    f"{next_season['season']} marriage season starts in {next_season['days_away']} days. "
                    f"Plan dispatch for: {', '.join(next_season['recommended_colours'][:3])}."
                ),
                "related_festival": "Marriage Season",
                "action_required": True,
                "is_dismissed": False,
                "created_at": str(today),
            })
            alert_id += 1

    # 3. Slow-moving SKU alerts
    sku_perf = get_sku_performance(db)
    slow_movers = [s for s in sku_perf if s["is_slow_moving"]]
    if slow_movers:
        slow_names = ", ".join(f"{s['model_name']} {s['colour']}" for s in slow_movers[:3])
        alerts.append({
            "id": alert_id,
            "alert_type": "slow_moving_inventory",
            "priority": "high" if len(slow_movers) >= 5 else "medium",
            "title": f"{len(slow_movers)} Slow-Moving SKU(s) Detected",
            "message": (
                f"The following SKUs show low sales velocity: {slow_names}"
                f"{' and more' if len(slow_movers) > 3 else ''}. "
                "Consider promotional pricing or reducing dispatch quantities to avoid dead stock."
            ),
            "action_required": True,
            "is_dismissed": False,
            "created_at": str(today),
        })
        alert_id += 1

    # 4. YoY growth alert for top performer
    top = sku_perf[0] if sku_perf else None
    if top and top.get("yoy_growth_percent") and top["yoy_growth_percent"] > 20:
        alerts.append({
            "id": alert_id,
            "alert_type": "high_growth_sku",
            "priority": "low",
            "title": f"🚀 {top['model_name']} {top['colour']} Growing Fast (+{top['yoy_growth_percent']}% YoY)",
            "message": (
                f"{top['model_name']} {top['colour']} is your fastest growing SKU this year "
                f"with +{top['yoy_growth_percent']}% YoY growth. Ensure sufficient dispatch."
            ),
            "sku_code": top["sku_code"],
            "action_required": False,
            "is_dismissed": False,
            "created_at": str(today),
        })
        alert_id += 1

    # 5. Year-end clearance (Nov-Jan)
    if today.month in [11, 12, 1]:
        alerts.append({
            "id": alert_id,
            "alert_type": "year_end_clearance",
            "priority": "medium",
            "title": "Year-End Clearance Opportunity",
            "message": (
                "Financial year-end approaching. Dealers typically offer year-end schemes. "
                "Identify slow-moving variants for promotional clearance to free working capital."
            ),
            "action_required": True,
            "is_dismissed": False,
            "created_at": str(today),
        })
        alert_id += 1

    return sorted(alerts, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])


@router.get("/")
def get_alerts(db: Session = Depends(get_db)):
    return _generate_alerts(db)


@router.get("/critical")
def get_critical_alerts(db: Session = Depends(get_db)):
    return [a for a in _generate_alerts(db) if a["priority"] == "high"]


@router.get("/count")
def alert_count(db: Session = Depends(get_db)):
    alerts = _generate_alerts(db)
    return {
        "total": len(alerts),
        "high": len([a for a in alerts if a["priority"] == "high"]),
        "medium": len([a for a in alerts if a["priority"] == "medium"]),
        "low": len([a for a in alerts if a["priority"] == "low"]),
    }
