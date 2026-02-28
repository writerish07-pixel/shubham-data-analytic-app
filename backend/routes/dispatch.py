from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import csv
from datetime import date

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


@router.get("/export")
def export_dispatch_plan(
    lead_time_days: int = Query(21, ge=7, le=60),
    db: Session = Depends(get_db),
):
    """Export the dispatch plan as a downloadable CSV file."""
    recs = generate_dispatch_recommendations(db, lead_time_days=lead_time_days)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "SKU Code", "Model Name", "Variant", "Colour",
        "Current Stock (Uploaded)", "Stock Source",
        "Forecast Units (Next Period)", "Recommended Order Qty",
        "Buffer Stock (15%)", "Total Dispatch Qty",
        "Unit Price (₹)", "Working Capital Impact (₹)",
        "Festival Boost Factor", "Risk Score (%)", "Risk Type", "Notes",
    ])

    for r in recs:
        writer.writerow([
            r["sku_code"],
            r["model_name"],
            r["variant"],
            r["colour"],
            r.get("current_stock", 0),
            r.get("stock_source", "estimated"),
            int(r.get("forecast_units", 0)),
            r["recommended_quantity"],
            r["buffer_stock"],
            r["total_dispatch"],
            r["unit_price"],
            r["working_capital_impact"],
            r["festival_factor"],
            round(r["risk_score"] * 100, 1),
            r["risk_type"],
            r["notes"],
        ])

    output.seek(0)
    filename = f"dispatch_plan_{date.today().strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
