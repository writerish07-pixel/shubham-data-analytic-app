from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import csv
from datetime import date

from database import get_db
from services.dispatch_planner import (
    generate_dispatch_recommendations, working_capital_summary,
    generate_target_based_dispatch, stock_health_analysis,
    generate_sku_stock_plan,
)

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


@router.get("/target-plan/{year}/{month}")
def target_based_plan(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """Target-based dispatch plan — order exactly what you need to hit this month's target."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return generate_target_based_dispatch(db, year, month)


@router.get("/export-target/{year}/{month}")
def export_target_plan(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """Download target-based dispatch plan as CSV."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    plan = generate_target_based_dispatch(db, year, month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Plan Month", "Model", "Monthly Target", "Already Sold", "Remaining Target",
        "Current Stock", "Stock Source", "Festival Adjusted", "Buffer (15%)",
        "Order Quantity", "Daily Velocity", "Risk", "Notes",
    ])
    for r in plan.get("model_plans", []):
        writer.writerow([
            f"{plan['target_month']} {plan['target_year']}",
            r["model_name"],
            r["monthly_target"],
            r.get("already_sold", 0),
            r["remaining_target"],
            r["current_stock"],
            r["stock_source"],
            r["festival_adjusted"],
            r["buffer_stock"],
            r["order_quantity"],
            r.get("daily_velocity", 0),
            r["risk_type"],
            r.get("notes", ""),
        ])
    output.seek(0)
    filename = f"dispatch_{plan['target_month']}_{plan['target_year']}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/sku-stock-plan/{year}/{month}")
def sku_stock_plan(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """SKU-level stock order plan: sales target minus current stock, maintain 30-45 day buffer."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return generate_sku_stock_plan(db, year, month)


@router.get("/export-sku-stock-plan/{year}/{month}")
def export_sku_stock_plan(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """Download SKU-level stock plan as CSV."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    plan = generate_sku_stock_plan(db, year, month)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "SKU Code", "Model", "Colour",
        "Monthly Sales Target", "Current Stock", "Stock Source",
        "Stock After Sales", "Days Cover After Sales",
        "30-Day Min Buffer", "45-Day Max Buffer",
        "Order Qty (Min - 30d)", "Order Qty (Max - 45d)",
        "Status", "Notes",
    ])
    for r in plan.get("sku_plans", []):
        writer.writerow([
            r["sku_code"], r["model_name"], r["colour"],
            r["monthly_target"], r["current_stock"], r["stock_source"],
            r["stock_after_sales"], r["days_cover_after_sales"],
            r["min_buffer_30d"], r["max_buffer_45d"],
            r["order_qty_min"], r["order_qty_max"],
            r["status"], r["notes"],
        ])
    output.seek(0)
    filename = f"sku_stock_plan_{plan['target_month']}_{plan['target_year']}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/stock-health/{year}/{month}")
def dispatch_stock_health(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """Stock health vs monthly target — shows which models need urgent ordering."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")
    return stock_health_analysis(db, year, month)


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
