from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services.forecasting import (
    run_full_forecast, get_forecast_summary, what_if_simulation,
    compute_forecast_accuracy,
)
from schemas import WhatIfRequest

router = APIRouter()


@router.get("/")
def get_forecasts(
    horizon_days: int = Query(60, ge=7, le=120),
    db: Session = Depends(get_db),
):
    return run_full_forecast(db, horizon_days=horizon_days)


@router.get("/summary")
def forecast_summary(
    horizon_days: int = Query(60, ge=7, le=120),
    db: Session = Depends(get_db),
):
    return get_forecast_summary(db, horizon_days=horizon_days)


@router.get("/sku/{sku_code}")
def forecast_for_sku(
    sku_code: str,
    horizon_days: int = Query(60, ge=7, le=120),
    db: Session = Depends(get_db),
):
    all_fc = run_full_forecast(db, horizon_days=horizon_days)
    return [f for f in all_fc if f["sku_code"] == sku_code]


@router.get("/accuracy")
def forecast_accuracy(db: Session = Depends(get_db)):
    """Back-test forecast accuracy against the most recent full month in the data."""
    return compute_forecast_accuracy(db)


@router.post("/what-if")
def what_if(
    request: WhatIfRequest,
    db: Session = Depends(get_db),
):
    return what_if_simulation(
        db,
        scenario=request.scenario,
        parameter=request.parameter,
        sku_codes=request.sku_codes,
    )
