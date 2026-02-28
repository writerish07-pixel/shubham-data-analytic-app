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
    get_location_analysis, get_data_info,
)

router = APIRouter()

# Minimum columns the user must supply (after alias normalisation)
REQUIRED_COLUMNS = {"invoice_date", "sku_code", "model_name", "variant", "colour"}

# Accepted aliases: left = what user might write, right = canonical name
COLUMN_ALIASES = {
    # invoice date
    "sku":              "sku_code",
    "item_code":        "sku_code",
    "product_code":     "sku_code",
    "part_no":          "sku_code",
    "part_number":      "sku_code",
    # model name
    "model":            "model_name",
    "product_name":     "model_name",
    "item_name":        "model_name",
    "description":      "model_name",
    "product":          "model_name",
    "item":             "model_name",
    # variant
    "variant_name":     "variant",
    "type":             "variant",
    "grade":            "variant",
    # colour
    "color":            "colour",
    "shade":            "colour",
    "color_name":       "colour",
    "colour_name":      "colour",
    # invoice date
    "date":             "invoice_date",
    "sale_date":        "invoice_date",
    "inv_date":         "invoice_date",
    "invoice date":     "invoice_date",
    "bill_date":        "invoice_date",
    "sales_date":       "invoice_date",
    "transaction_date": "invoice_date",
    "txn_date":         "invoice_date",
    # quantity
    "qty":              "quantity_sold",
    "quantity":         "quantity_sold",
    "units":            "quantity_sold",
    "sold_qty":         "quantity_sold",
    "no_of_units":      "quantity_sold",
    "nos":              "quantity_sold",
    "pcs":              "quantity_sold",
    # price
    "price":            "unit_price",
    "rate":             "unit_price",
    "mrp":              "unit_price",
    "ex_showroom":      "unit_price",
    "selling_price":    "unit_price",
    # total value
    "amount":           "total_value",
    "value":            "total_value",
    "net_amount":       "total_value",
    "total":            "total_value",
    "total_amount":     "total_value",
    "invoice_amount":   "total_value",
    "bill_amount":      "total_value",
    # location / region
    "city":             "location",
    "dealer":           "location",
    "dealer_city":      "location",
    "zone":             "region",
    "area":             "region",
    "state":            "region",
    "territory":        "region",
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


@router.get("/data-info")
def data_info(db: Session = Depends(get_db)):
    """Return metadata about the currently loaded sales data — date range, record count, years available."""
    return get_data_info(db)


@router.get("/location-analysis")
def location_analysis(db: Session = Depends(get_db)):
    """Sales breakdown by location (city/dealer) and region."""
    return get_location_analysis(db)


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


@router.delete("/clear")
def clear_sales_data(db: Session = Depends(get_db)):
    """Delete all existing sales records (resets the database for fresh upload)."""
    count = db.query(HeroSalesData).count()
    db.query(HeroSalesData).delete()
    db.commit()
    return {"status": "cleared", "rows_deleted": count}


@router.post("/upload")
def upload_sales_data(
    file: UploadFile = File(...),
    replace_existing: bool = True,
    db: Session = Depends(get_db),
):
    """
    Upload sales data from a CSV or Excel file.

    replace_existing=True (default): clears all previous records before inserting.
    replace_existing=False: appends to existing data.

    Required columns (flexible naming accepted):
      invoice_date / date / sale_date / inv_date / bill_date
      sku_code / sku / item_code / product_code
      model_name / model / product_name / item_name / description
      variant / variant_name / type
      colour / color / shade

    Optional columns:
      quantity_sold / qty / quantity / units / sold_qty  → defaults to 1 per row
      unit_price / price / rate / mrp                   → defaults to 0
      total_value / amount / value / net_amount / total → defaults to quantity × unit_price
      location / city / dealer / dealer_city
      region / zone / area / state
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

    # If replacing, clear existing data first
    if replace_existing:
        db.query(HeroSalesData).delete()
        db.commit()

    # Normalise column names and apply aliases
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)

    # Auto-detect model_name from sku_code if model_name column is missing
    if "model_name" not in df.columns and "sku_code" in df.columns:
        df["model_name"] = df["sku_code"].astype(str).apply(
            lambda s: s.split("-")[1] if "-" in s and len(s.split("-")) > 1 else s
        )

    # Auto-fill variant if missing
    if "variant" not in df.columns:
        df["variant"] = "Standard"

    # Auto-fill colour if missing
    if "colour" not in df.columns:
        df["colour"] = "Default"

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
        "replaced_existing": replace_existing,
        "errors": errors[:20],
    }
