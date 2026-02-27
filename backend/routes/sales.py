from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import io
import csv
import pandas as pd
from datetime import date

from database import get_db
from models import HeroSalesData
from services.sales_analytics import (
    get_yoy_analysis, get_mom_analysis, get_sku_performance,
    get_colour_analysis, get_seasonal_patterns, get_dashboard_summary,
)

router = APIRouter()

REQUIRED_COLUMNS = {"invoice_date", "sku_code", "model_name", "variant", "colour", "quantity_sold", "unit_price", "total_value"}
OPTIONAL_COLUMNS = {"location", "region"}


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


@router.get("/upload/template")
def download_template():
    """Return a CSV template showing the required columns for data upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "invoice_date", "sku_code", "model_name", "variant", "colour",
        "quantity_sold", "unit_price", "total_value", "location", "region"
    ])
    writer.writerow([
        "2024-01-15", "HER-SPL-STD-BLK", "Splendor Plus", "Standard", "Black",
        "3", "72000", "216000", "Delhi", "North India"
    ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_upload_template.csv"},
    )


@router.post("/upload")
def upload_sales_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload sales data from a CSV or Excel file.

    Required columns: invoice_date, sku_code, model_name, variant, colour,
                      quantity_sold, unit_price, total_value
    Optional columns: location, region

    invoice_date format: YYYY-MM-DD
    """
    filename = file.filename or ""
    content = file.file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files are supported.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
                   f"Download the template from GET /api/sales/upload/template"
        )

    rows_inserted = 0
    rows_skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            invoice_date = pd.to_datetime(row["invoice_date"]).date()
            record = HeroSalesData(
                invoice_date=invoice_date,
                sku_code=str(row["sku_code"]).strip(),
                model_name=str(row["model_name"]).strip(),
                variant=str(row["variant"]).strip(),
                colour=str(row["colour"]).strip(),
                quantity_sold=int(row["quantity_sold"]),
                unit_price=float(row["unit_price"]),
                total_value=float(row["total_value"]),
                location=str(row["location"]).strip() if "location" in df.columns and pd.notna(row.get("location")) else None,
                region=str(row["region"]).strip() if "region" in df.columns and pd.notna(row.get("region")) else None,
            )
            db.add(record)
            rows_inserted += 1
        except Exception as e:
            rows_skipped += 1
            errors.append({"row": int(idx) + 2, "error": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error while saving: {e}")

    return {
        "status": "success",
        "filename": filename,
        "rows_inserted": rows_inserted,
        "rows_skipped": rows_skipped,
        "errors": errors[:20],  # return at most 20 error details
    }
