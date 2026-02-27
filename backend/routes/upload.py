"""
Data Upload API
Accepts CSV / Excel files, validates the schema, and replaces the sales dataset.
"""
import io
import logging
from datetime import date, datetime
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from models import HeroSalesData

logger = logging.getLogger(__name__)

router = APIRouter()

# Required columns that must be present in the uploaded file
REQUIRED_COLUMNS = {"invoice_date", "sku_code", "model_name", "variant", "colour"}

# Optional columns with their default values
OPTIONAL_COLUMNS: Dict[str, Any] = {
    "quantity_sold": 1,
    "unit_price": 0.0,
    "total_value": None,   # auto-calculated when missing
    "location": None,
    "region": None,
}


def _parse_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded bytes into a DataFrame depending on file extension."""
    fname = filename.lower()
    if fname.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    elif fname.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a CSV or Excel (.xlsx) file.",
        )
    return df


def _validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Validate required columns exist and clean / coerce types."""
    # Normalise column names (strip whitespace, lower-case)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
                   f"Required: {', '.join(sorted(REQUIRED_COLUMNS))}",
        )

    # Fill optional columns with defaults
    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default

    # Parse invoice_date
    try:
        df["invoice_date"] = pd.to_datetime(df["invoice_date"]).dt.date
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Column 'invoice_date' could not be parsed. Use YYYY-MM-DD format.",
        )

    # Coerce numeric columns
    df["quantity_sold"] = pd.to_numeric(df["quantity_sold"], errors="coerce").fillna(1).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)

    # Auto-calculate total_value when missing / zero
    mask = df["total_value"].isna() | (df["total_value"] == 0)
    df.loc[mask, "total_value"] = df.loc[mask, "quantity_sold"] * df.loc[mask, "unit_price"]
    df["total_value"] = pd.to_numeric(df["total_value"], errors="coerce").fillna(0.0)

    # Drop rows with null required fields
    df = df.dropna(subset=list(REQUIRED_COLUMNS))

    if df.empty:
        raise HTTPException(status_code=422, detail="No valid rows found after validation.")

    return df


@router.post("/")
def upload_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV or Excel file to replace the current sales dataset.

    Required columns: invoice_date, sku_code, model_name, variant, colour
    Optional columns: quantity_sold, unit_price, total_value, location, region
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        df = _parse_dataframe(content, file.filename)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to parse uploaded file: %s", exc)
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")

    df = _validate_and_clean(df)

    now = datetime.utcnow()
    records = []
    for _, row in df.iterrows():
        records.append(
            HeroSalesData(
                invoice_date=row["invoice_date"],
                sku_code=str(row["sku_code"]).strip(),
                model_name=str(row["model_name"]).strip(),
                variant=str(row["variant"]).strip(),
                colour=str(row["colour"]).strip(),
                quantity_sold=int(row["quantity_sold"]),
                unit_price=float(row["unit_price"]),
                total_value=float(row["total_value"]),
                location=str(row["location"]).strip() if pd.notna(row["location"]) else None,
                region=str(row["region"]).strip() if pd.notna(row["region"]) else None,
                source_type="uploaded",
                uploaded_at=now,
            )
        )

    try:
        # Replace all existing data with the uploaded dataset
        db.query(HeroSalesData).delete()
        batch_size = 500
        for i in range(0, len(records), batch_size):
            db.bulk_save_objects(records[i:i + batch_size])
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Database error during upload: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save data to the database.")

    # Build summary
    dates = [r.invoice_date for r in records]
    skus = {r.sku_code for r in records}
    models = {r.model_name for r in records}

    return {
        "success": True,
        "message": f"Successfully imported {len(records):,} records.",
        "summary": {
            "total_rows": len(records),
            "date_range": {
                "from": str(min(dates)),
                "to": str(max(dates)),
            },
            "unique_skus": len(skus),
            "unique_models": len(models),
            "uploaded_at": now.isoformat(),
        },
    }


@router.get("/status")
def upload_status(db: Session = Depends(get_db)):
    """Return information about the current dataset (source and size)."""
    total = db.query(HeroSalesData).count()
    uploaded_count = db.query(HeroSalesData).filter(HeroSalesData.source_type == "uploaded").count()
    sample_count = db.query(HeroSalesData).filter(HeroSalesData.source_type == "sample").count()

    source = "uploaded" if uploaded_count > 0 else "sample"
    last_upload = None
    if uploaded_count > 0:
        row = (
            db.query(HeroSalesData.uploaded_at)
            .filter(HeroSalesData.source_type == "uploaded")
            .order_by(HeroSalesData.uploaded_at.desc())
            .first()
        )
        if row and row[0]:
            last_upload = row[0].isoformat()

    return {
        "total_records": total,
        "source": source,
        "uploaded_records": uploaded_count,
        "sample_records": sample_count,
        "last_upload": last_upload,
    }
