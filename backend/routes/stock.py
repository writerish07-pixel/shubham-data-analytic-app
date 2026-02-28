"""
Stock Inventory Routes
Upload and manage current on-hand stock to adjust dispatch recommendations.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import csv
import pandas as pd

from database import get_db
from models import StockInventory

router = APIRouter()

# Accepted column name aliases → canonical name
STOCK_ALIASES = {
    # sku
    "sku":              "sku_code",
    "item_code":        "sku_code",
    "product_code":     "sku_code",
    "part_no":          "sku_code",
    "part_number":      "sku_code",
    "code":             "sku_code",
    # model name
    "model":            "model_name",
    "product_name":     "model_name",
    "item_name":        "model_name",
    "description":      "model_name",
    "product":          "model_name",
    "item":             "model_name",
    "name":             "model_name",
    # variant
    "variant_name":     "variant",
    "type":             "variant",
    "grade":            "variant",
    # colour
    "color":            "colour",
    "shade":            "colour",
    "color_name":       "colour",
    "colour_name":      "colour",
    # stock quantity
    "stock":            "current_stock",
    "qty":              "current_stock",
    "quantity":         "current_stock",
    "available_qty":    "current_stock",
    "stock_qty":        "current_stock",
    "inventory":        "current_stock",
    "on_hand":          "current_stock",
    "balance":          "current_stock",
    "balance_qty":      "current_stock",
    "closing_stock":    "current_stock",
    "available":        "current_stock",
    "units":            "current_stock",
    # location
    "city":             "location",
    "dealer":           "location",
    "warehouse":        "location",
    "godown":           "location",
    # region
    "zone":             "region",
    "area":             "region",
    "state":            "region",
    "territory":        "region",
}


@router.get("/template")
def stock_template():
    """Download a CSV template for stock inventory upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sku_code", "model_name", "variant", "colour", "current_stock", "location", "region"])
    writer.writerow(["HER-SPL-STD-BLK", "Splendor Plus", "Standard", "Black", "45", "Delhi", "North India"])
    writer.writerow(["HER-HFD-STD-RED", "HF Deluxe", "Standard", "Red", "30", "Mumbai", "West India"])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_inventory_template.csv"},
    )


@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """Return all current stock inventory items."""
    items = db.query(StockInventory).order_by(StockInventory.model_name).all()
    return [
        {
            "id": i.id,
            "sku_code": i.sku_code,
            "model_name": i.model_name,
            "variant": i.variant,
            "colour": i.colour,
            "current_stock": i.current_stock,
            "location": i.location,
            "region": i.region,
        }
        for i in items
    ]


@router.get("/summary")
def stock_summary(db: Session = Depends(get_db)):
    """Return aggregated stock summary."""
    items = db.query(StockInventory).all()
    if not items:
        return {"total_skus": 0, "total_units": 0, "items": []}
    total_units = sum(i.current_stock for i in items)
    return {
        "total_skus": len(items),
        "total_units": total_units,
        "has_stock_data": True,
    }


@router.delete("/clear")
def clear_inventory(db: Session = Depends(get_db)):
    """Remove all stock inventory records."""
    count = db.query(StockInventory).count()
    db.query(StockInventory).delete()
    db.commit()
    return {"status": "cleared", "rows_deleted": count}


@router.post("/upload")
def upload_stock(
    file: UploadFile = File(...),
    replace_existing: bool = True,
    db: Session = Depends(get_db),
):
    """
    Upload current stock inventory from CSV or Excel.

    Required columns (flexible naming):
      sku_code / sku / item_code / product_code
      current_stock / stock / qty / quantity / available_qty / balance

    Optional columns:
      model_name / model / product_name / item_name
      variant / type / grade
      colour / color
      location / city / warehouse / dealer
      region / zone / state / area
    """
    filename = file.filename or ""
    content = file.file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only .csv, .xlsx, or .xls files supported.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=STOCK_ALIASES, inplace=True)

    # Must have at least sku_code and current_stock
    if "sku_code" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="Missing SKU column. Accepted names: sku_code, sku, item_code, product_code, part_no, code"
        )
    if "current_stock" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="Missing stock quantity column. Accepted names: current_stock, stock, qty, quantity, available_qty, balance, on_hand, closing_stock"
        )

    if replace_existing:
        db.query(StockInventory).delete()
        db.commit()

    cols = set(df.columns)
    rows_inserted = 0
    rows_skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            sku = str(row["sku_code"]).strip()
            if not sku or sku.lower() in ("nan", "none", ""):
                rows_skipped += 1
                continue

            stock_val = row["current_stock"]
            if pd.isna(stock_val):
                stock_val = 0
            stock = int(float(str(stock_val).replace(",", "")))

            record = StockInventory(
                sku_code=sku,
                model_name=str(row["model_name"]).strip() if "model_name" in cols and pd.notna(row.get("model_name")) else sku,
                variant=str(row["variant"]).strip() if "variant" in cols and pd.notna(row.get("variant")) else "Standard",
                colour=str(row["colour"]).strip() if "colour" in cols and pd.notna(row.get("colour")) else "Default",
                current_stock=stock,
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
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return {
        "status": "success",
        "filename": filename,
        "rows_inserted": rows_inserted,
        "rows_skipped": rows_skipped,
        "replaced_existing": replace_existing,
        "errors": errors[:20],
    }
