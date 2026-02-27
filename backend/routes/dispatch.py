from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.dispatch_planner import generate_dispatch_recommendations, working_capital_summary

router = APIRouter()


@router.get("/recommendations")
def dispatch_recommendations(
    lead_time_days: int = Query(21, ge=7, le=60),
    db: Session = Depends(get_db),
):
    return generate_dispatch_recommendations(db, lead_time_days=lead_time_days)


@router.get("/working-capital")
def working_capital(db: Session = Depends(get_db)):
    return working_capital_summary(db)


@router.get("/risk-scores")
def risk_scores(db: Session = Depends(get_db)):
    recs = generate_dispatch_recommendations(db)
    return [
        {
            "sku_code": r["sku_code"],
            "model_name": r["model_name"],
            "colour": r["colour"],
            "risk_score": r["risk_score"],
            "risk_type": r["risk_type"],
        }
        for r in recs
    ]
