from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.festival_calendar import (
    get_upcoming_festivals, get_festival_impact_history,
    get_marriage_season_info, get_all_festivals_flat,
    is_marriage_season,
)
from datetime import date

router = APIRouter()


@router.get("/upcoming")
def upcoming_festivals(
    days_ahead: int = Query(90, ge=7, le=365),
):
    upcoming = get_upcoming_festivals(days_ahead=days_ahead)
    return [
        {
            **f,
            "date": str(f["date"]),
        }
        for f in upcoming
    ]


@router.get("/calendar")
def full_calendar():
    festivals = get_all_festivals_flat()
    return [
        {**f, "date": str(f["date"])}
        for f in festivals
    ]


@router.get("/impact/{festival_name}")
def festival_impact(festival_name: str):
    history = get_festival_impact_history(festival_name)
    return [{"year": h["year"], "date": str(h["date"]), "impact_pct": h["impact_pct"]} for h in history]


@router.get("/marriage-season")
def marriage_season():
    info = get_marriage_season_info()
    in_season, season_data = is_marriage_season()
    return {
        "currently_in_season": in_season,
        "current_season": season_data,
        "next_season": info,
    }
