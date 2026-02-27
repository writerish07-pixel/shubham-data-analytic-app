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

# Minimum columns the user must supply (after alias normalisation)
REQUIRED_COLUMNS = {"invoice_date", "sku_code", "model_name", "variant", "colour"}

# Accepted aliases: left = what user might write, right = canonical name
COLUMN_ALIASES = {
    "sku":        "sku_code",
    "model":      "model_name",
    "color":      "colour",
    "date":       "invoice_date",
    "sale_date":  "invoice_date",
    "qty":        "quantity_sold",
    "quantity":   "quantity_sold",
    "units":      "quantity_sold",
    "price":      "unit_price",
    "amount":     "total_value",
    "value":      "total_value",
}


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
    # Minimal template matching user's real file format
    writer.writerow(["invoice_date", "sku_code", "model_name", "variant", "colour", "location", "region"])
    writer.writerow(["2024-01-15", "HER-SPL-STD-BLK", "Splendor Plus", "Standard", "Black", "Delhi", "North India"])
    writer.writerow(["2024-01-15", "HER-HFD-STD-RED", "HF Deluxe", "Standard", "Red", "Mumbai", "West India"])
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

    Required columns (flexible naming accepted):
      invoice_date / date / sale_date
      sku_code / sku
      model_name / model
      variant
      colour / color

    Optional columns:
      quantity_sold / qty / quantity / units  → defaults to 1 per row
      unit_price / price                      → defaults to 0
      total_value / amount / value            → defaults to quantity × unit_price
      location
      region

    invoice_date format: YYYY-MM-DD  (or any parseable date format)
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

    # Normalise column names and apply aliases
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
                   f"Accepted aliases — sku_code: 'sku', model_name: 'model', colour: 'color', "
                   f"invoice_date: 'date'/'sale_date'. Download template for reference."
        )

    cols = set(df.columns)
    rows_inserted = 0
    rows_skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            invoice_date = pd.to_datetime(row["invoice_date"]).date()

            # quantity: default 1 per row if not supplied
            qty = int(row["quantity_sold"]) if "quantity_sold" in cols and pd.notna(row.get("quantity_sold")) else 1

            # price: default 0 if not supplied
            price = float(row["unit_price"]) if "unit_price" in cols and pd.notna(row.get("unit_price")) else 0.0

            # total_value: quantity × price if not explicitly supplied
            if "total_value" in cols and pd.notna(row.get("total_value")):
                total = float(row["total_value"])
            else:
                total = round(qty * price, 2)

            record = HeroSalesData(
                invoice_date=invoice_date,
                sku_code=str(row["sku_code"]).strip(),
                model_name=str(row["model_name"]).strip(),
                variant=str(row["variant"]).strip(),
                colour=str(row["colour"]).strip(),
                quantity_sold=qty,
                unit_price=price,
                total_value=total,
                location=str(row["location"]).strip() if "location" in cols and pd.notna(row.get("location")) else None,
                region=str(row["region"]).strip() if "region" in cols and pd.notna(row.get("region")) else None,
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
        "errors": errors[:20],
    }
