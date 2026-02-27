from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services.sales_analytics import (
    get_yoy_analysis, get_mom_analysis, get_sku_performance,
    get_colour_analysis, get_seasonal_patterns, get_dashboard_summary,
)

router = APIRouter()


@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db)):
    return get_dashboard_summary(db)


@router.get("/yoy")
def yoy_analysis(db: Session = Depends(get_db)):
    return get_yoy_analysis(db)


@router.get("/mom")
def mom_analysis(
    months: int = Query(24, ge=2, le=60),
    db: Session = Depends(get_db),
):
    return get_mom_analysis(db, recent_months=months)


@router.get("/sku-performance")
def sku_performance(db: Session = Depends(get_db)):
    return get_sku_performance(db)


@router.get("/top-performers")
def top_performers(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return get_sku_performance(db)[:limit]


@router.get("/slow-movers")
def slow_movers(db: Session = Depends(get_db)):
    all_skus = get_sku_performance(db)
    return [s for s in all_skus if s["is_slow_moving"]]


@router.get("/colour-analysis")
def colour_analysis(db: Session = Depends(get_db)):
    return get_colour_analysis(db)


@router.get("/seasonal-patterns")
def seasonal_patterns(db: Session = Depends(get_db)):
    return get_seasonal_patterns(db)
