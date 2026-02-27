"""
Sample Data Generator
Generates 4 years (2021–2024) of realistic Indian two-wheeler sales data
with festive/marriage seasonality, YoY growth, and SKU mix.
"""
import random
import logging
from datetime import date, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

# ─── SKU Master ─────────────────────────────────────────────────────────────────
HERO_SKUS = [
    {"sku_code": "HER-SPL-STD-BLK", "model_name": "Splendor Plus",    "variant": "Standard",  "colour": "Black",         "price": 72000,  "base_daily": 4.5, "region": "North India"},
    {"sku_code": "HER-SPL-STD-RED", "model_name": "Splendor Plus",    "variant": "Standard",  "colour": "Sports Red",    "price": 72000,  "base_daily": 3.8, "region": "North India"},
    {"sku_code": "HER-SPL-DLX-SIL", "model_name": "Splendor Plus",    "variant": "Deluxe",    "colour": "Pearl Silver",  "price": 76000,  "base_daily": 3.2, "region": "North India"},
    {"sku_code": "HER-HFD-STD-BLK", "model_name": "HF Deluxe",        "variant": "Standard",  "colour": "Black",         "price": 64000,  "base_daily": 5.0, "region": "All India"},
    {"sku_code": "HER-HFD-STD-RED", "model_name": "HF Deluxe",        "variant": "Standard",  "colour": "Red",           "price": 64000,  "base_daily": 4.0, "region": "All India"},
    {"sku_code": "HER-PAS-STD-BLK", "model_name": "Passion Pro",      "variant": "Standard",  "colour": "Black",         "price": 79000,  "base_daily": 3.5, "region": "All India"},
    {"sku_code": "HER-PAS-DLX-RED", "model_name": "Passion Pro",      "variant": "Deluxe",    "colour": "Red",           "price": 82000,  "base_daily": 2.5, "region": "All India"},
    {"sku_code": "HER-XTR-STD-RED", "model_name": "Xtreme 160R",      "variant": "Standard",  "colour": "Blazing Red",   "price": 115000, "base_daily": 2.0, "region": "Urban"},
    {"sku_code": "HER-XTR-STD-BLK", "model_name": "Xtreme 160R",      "variant": "Standard",  "colour": "Black",         "price": 115000, "base_daily": 1.8, "region": "Urban"},
    {"sku_code": "HER-DST-STD-WHT", "model_name": "Destini 125",      "variant": "Standard",  "colour": "Pearl White",   "price": 78000,  "base_daily": 2.8, "region": "All India"},
    {"sku_code": "HER-DST-STD-RED", "model_name": "Destini 125",      "variant": "Standard",  "colour": "Imperial Red",  "price": 78000,  "base_daily": 2.5, "region": "All India"},
    {"sku_code": "HER-MAE-STD-SIL", "model_name": "Maestro Edge 125", "variant": "Standard",  "colour": "Silver",        "price": 82000,  "base_daily": 2.0, "region": "South India"},
    {"sku_code": "HER-GLM-STD-BLU", "model_name": "Glamour",          "variant": "Standard",  "colour": "Force Blue",    "price": 85000,  "base_daily": 1.5, "region": "All India"},
    {"sku_code": "HER-XPL-STD-BLK", "model_name": "Xpulse 200",       "variant": "Standard",  "colour": "Sports Red",    "price": 140000, "base_daily": 0.8, "region": "Urban"},
    {"sku_code": "HER-SUP-STD-BLK", "model_name": "Super Splendor",   "variant": "Standard",  "colour": "Black",         "price": 82000,  "base_daily": 2.2, "region": "All India"},
]

# Monthly seasonal multipliers (Indian two-wheeler market)
SEASONAL = {
    1: 0.85, 2: 0.92, 3: 1.15, 4: 0.95, 5: 1.00,
    6: 0.82, 7: 0.78, 8: 0.95, 9: 1.08, 10: 1.38,
    11: 1.52, 12: 1.22,
}

# Festival date windows: (month, start_day, end_day, boost_multiplier)
FESTIVAL_WINDOWS = {
    2021: [(1, 12, 16, 1.30), (10, 5, 16, 1.40), (11, 1, 7, 1.60)],
    2022: [(1, 12, 16, 1.30), (9, 25, 30, 1.20), (10, 1, 6, 1.40), (10, 22, 26, 1.60)],
    2023: [(1, 12, 16, 1.30), (4, 20, 24, 1.25), (10, 14, 25, 1.40), (11, 10, 15, 1.60)],
    2024: [(1, 13, 17, 1.30), (5, 8, 12, 1.25), (10, 2, 14, 1.40), (10, 28, 31, 1.50), (11, 1, 5, 1.60)],
}

# YoY growth factors
YOY_GROWTH = {2021: 1.00, 2022: 1.08, 2023: 1.14, 2024: 1.22}


def _is_festival_day(check_date: date) -> float:
    """Return festival boost multiplier for a given date."""
    year = check_date.year
    windows = FESTIVAL_WINDOWS.get(year, [])
    for (month, start_day, end_day, boost) in windows:
        if check_date.month == month and start_day <= check_date.day <= end_day:
            return boost
    return 1.0


def _is_marriage_season(check_date: date) -> float:
    """Return marriage-season demand uplift."""
    m = check_date.month
    if m in [11, 12]:
        return 1.25
    if m in [2, 3, 4, 5]:
        return 1.20
    return 1.0


def _generate_daily_qty(base_daily: float, invoice_date: date, yoy: float, noise_seed: int) -> int:
    """Compute units sold on a given day for one SKU."""
    random.seed(noise_seed)
    seasonal = SEASONAL[invoice_date.month]
    festival = _is_festival_day(invoice_date)
    marriage = _is_marriage_season(invoice_date)
    noise = random.uniform(0.7, 1.3)  # day-level randomness

    raw = base_daily * seasonal * festival * marriage * yoy * noise
    qty = max(0, round(raw))
    return qty


def generate_sales_records() -> List[Dict]:
    """Generate full 4-year sales dataset."""
    records = []
    start = date(2021, 1, 1)
    end = date(2024, 12, 31)

    seed_counter = 0
    current = start
    while current <= end:
        yoy = YOY_GROWTH.get(current.year, 1.0)
        for sku in HERO_SKUS:
            seed_counter += 1
            qty = _generate_daily_qty(sku["base_daily"], current, yoy, seed_counter)
            if qty == 0:
                continue  # no sales this day for this SKU

            # slight price drift YoY (~3% annual increase)
            price_drift = 1.0 + 0.03 * (current.year - 2021)
            price = round(sku["price"] * price_drift, -2)  # round to nearest ₹100

            records.append({
                "invoice_date": current,
                "sku_code": sku["sku_code"],
                "model_name": sku["model_name"],
                "variant": sku["variant"],
                "colour": sku["colour"],
                "quantity_sold": qty,
                "unit_price": price,
                "total_value": round(qty * price, 2),
                "location": "Delhi" if "North" in sku["region"] else
                            "Chennai" if "South" in sku["region"] else
                            "Mumbai" if "Urban" in sku["region"] else "Pan India",
                "region": sku["region"],
            })
        current += timedelta(days=1)

    logger.info(f"Generated {len(records)} sales records.")
    return records


def seed_if_empty():
    """Insert sample data only if the HeroSalesData table is empty."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from database import SessionLocal
    from models import HeroSalesData

    db = SessionLocal()
    try:
        count = db.query(HeroSalesData).count()
        if count > 0:
            logger.info(f"Database already has {count} records – skipping seed.")
            return

        logger.info("Seeding database with sample sales data (this may take a moment)…")
        records = generate_sales_records()

        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i: i + batch_size]
            db.bulk_insert_mappings(HeroSalesData, batch)
            db.commit()

        logger.info(f"Seeded {len(records)} records successfully.")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    seed_if_empty()
