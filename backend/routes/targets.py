"""
Sales Target API
────────────────────────────────────────────────────────────────────────
GET  /api/targets/month/{year}/{month}         — targets + actuals for a month
GET  /api/targets/pathway/{year}/{month}       — achievement pathway
GET  /api/targets/year/{year}                  — full 12-month plan
GET  /api/targets/auto/{year}/{month}          — auto-computed target (preview)
POST /api/targets/overall/{year}/{month}       — save/update overall target
POST /api/targets/model/{year}/{month}         — save model-wise target
DELETE /api/targets/model/{year}/{month}/{model} — remove model target
GET  /api/targets/models                       — all model names in data
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from services.target_engine import (
    compute_auto_target, save_overall_target, save_model_target,
    get_targets_for_month, get_target_pathway, get_full_year_target_plan,
    delete_model_target, get_sku_targets, MIN_GROWTH_PCT,
)
from services.sales_analytics import get_all_model_names

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class OverallTargetIn(BaseModel):
    target_units: int
    growth_pct:   float = MIN_GROWTH_PCT
    notes:        Optional[str] = ""

class ModelTargetIn(BaseModel):
    model_name:   str
    target_units: int
    notes:        Optional[str] = ""


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/month/{year}/{month}")
def targets_for_month(year: int, month: int, db: Session = Depends(get_db)):
    """Return overall + model targets and actuals for a given month."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return get_targets_for_month(db, year, month)


@router.get("/pathway/{year}/{month}")
def target_pathway(year: int, month: int, db: Session = Depends(get_db)):
    """Return daily run-rate, weekly plan, risk level, and key actions to hit target."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return get_target_pathway(db, year, month)


@router.get("/year/{year}")
def full_year_plan(year: int, db: Session = Depends(get_db)):
    """Return all 12 months' targets + actuals for the year (annual planning view)."""
    return get_full_year_target_plan(db, year)


@router.get("/auto/{year}/{month}")
def auto_target_preview(
    year: int,
    month: int,
    growth_pct: float = Query(MIN_GROWTH_PCT, ge=0, le=200),
    model: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Preview auto-computed target before saving."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return compute_auto_target(db, year, month, model=model, growth_pct=growth_pct)


@router.post("/overall/{year}/{month}")
def set_overall_target(
    year: int,
    month: int,
    body: OverallTargetIn,
    db: Session = Depends(get_db),
):
    """Save or update the overall monthly target."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    from services.target_engine import _sales_df, _last_year_same_month
    df = _sales_df(db)
    basis = _last_year_same_month(df, year, month)
    rec = save_overall_target(
        db, year, month,
        target_units=body.target_units,
        growth_pct=body.growth_pct,
        basis_units=basis,
        is_manual=True,
        notes=body.notes or "",
    )
    return {"status": "saved", "year": year, "month": month, "target_units": rec.target_units}


@router.post("/model/{year}/{month}")
def set_model_target(
    year: int,
    month: int,
    body: ModelTargetIn,
    db: Session = Depends(get_db),
):
    """Save or update a model-wise target. Overall target auto-adjusts to sum."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    rec = save_model_target(
        db, year, month,
        model_name=body.model_name,
        target_units=body.target_units,
        notes=body.notes or "",
    )
    return {
        "status": "saved",
        "model_name": rec.model_name,
        "target_units": rec.target_units,
        "growth_pct": rec.growth_pct,
    }


@router.delete("/model/{year}/{month}/{model_name}")
def remove_model_target(
    year: int,
    month: int,
    model_name: str,
    db: Session = Depends(get_db),
):
    """Remove a model-wise target (reverts to auto for that model)."""
    deleted = delete_model_target(db, year, month, model_name)
    return {"status": "deleted" if deleted else "not_found"}


@router.get("/sku-targets/{year}/{month}")
def sku_targets(year: int, month: int, db: Session = Depends(get_db)):
    """Return SKU-wise targets distributed from model targets by sales mix."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return get_sku_targets(db, year, month)


@router.get("/models")
def all_models(db: Session = Depends(get_db)):
    """Return all model names present in the uploaded sales data."""
    return {"models": get_all_model_names(db)}
