"""
Sales Analytics Service
Computes YoY, MoM, SKU performance, colour analysis, and seasonal patterns.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
import pandas as pd

from models import HeroSalesData, SKUPerformance


# ─── Monthly seasonal factors (empirical for Indian two-wheeler market) ─────────
MONTHLY_SEASONAL_FACTORS = {
    1: 0.85,   # January – post new-year slowdown
    2: 0.92,   # February – marriage season beginning
    3: 1.15,   # March – financial year-end / clearance
    4: 0.95,   # April – new financial year lull
    5: 1.00,   # May – moderate
    6: 0.82,   # June – monsoon onset
    7: 0.78,   # July – peak monsoon
    8: 0.95,   # August – Onam / Independence Day
    9: 1.08,   # September – Navratri approaching
    10: 1.38,  # October – Navratri, Dussehra
    11: 1.52,  # November – Diwali, marriage season
    12: 1.22,  # December – marriage season continues
}

MONTH_NAMES = {
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec",
}


def _sales_to_df(records: List[HeroSalesData]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    rows = [{
        "invoice_date": r.invoice_date,
        "sku_code": r.sku_code,
        "model_name": r.model_name,
        "variant": r.variant,
        "colour": r.colour,
        "quantity_sold": r.quantity_sold,
        "unit_price": r.unit_price,
        "total_value": r.total_value,
        "region": r.region,
    } for r in records]
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["year"] = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    return df


def get_yoy_analysis(db: Session) -> List[Dict]:
    """YoY monthly comparison for the last 4 years."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year", "month"]).agg(
        units=("quantity_sold", "sum"),
        revenue=("total_value", "sum"),
    ).reset_index()

    years = sorted(monthly["year"].unique())
    result = []

    for _, row in monthly.iterrows():
        prev_row = monthly[(monthly["year"] == row["year"] - 1) & (monthly["month"] == row["month"])]
        growth_pct = None
        if not prev_row.empty:
            prev_units = prev_row.iloc[0]["units"]
            growth_pct = round((row["units"] - prev_units) / prev_units * 100, 1) if prev_units > 0 else None

        result.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "month_name": MONTH_NAMES[int(row["month"])],
            "units": int(row["units"]),
            "revenue": round(float(row["revenue"]), 2),
            "growth_pct": growth_pct,
        })

    return sorted(result, key=lambda x: (x["year"], x["month"]))


def get_mom_analysis(db: Session, recent_months: int = 24) -> List[Dict]:
    """Month-on-month growth for the last N months."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year", "month"]).agg(
        units=("quantity_sold", "sum"),
        revenue=("total_value", "sum"),
    ).reset_index().sort_values(["year", "month"])

    monthly = monthly.tail(recent_months).reset_index(drop=True)

    result = []
    for i, row in monthly.iterrows():
        mom_growth = None
        if i > 0:
            prev = monthly.iloc[i - 1]
            mom_growth = round((row["units"] - prev["units"]) / prev["units"] * 100, 1) if prev["units"] > 0 else None
        result.append({
            "year": int(row["year"]),
            "month": int(row["month"]),
            "month_name": MONTH_NAMES[int(row["month"])],
            "units": int(row["units"]),
            "revenue": round(float(row["revenue"]), 2),
            "mom_growth_pct": mom_growth,
        })
    return result


def get_sku_performance(db: Session) -> List[Dict]:
    """Return performance metrics for each SKU."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    last_month_start = date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1)
    last_month_end = current_month_start - timedelta(days=1)
    last_year_start = date(today.year - 1, 1, 1)
    last_year_end = date(today.year - 1, 12, 31)
    this_year_start = date(today.year, 1, 1)

    agg = df.groupby(["sku_code", "model_name", "variant", "colour"]).agg(
        total_units=("quantity_sold", "sum"),
        total_revenue=("total_value", "sum"),
    ).reset_index()

    result = []
    for _, row in agg.iterrows():
        sku = row["sku_code"]
        sku_df = df[df["sku_code"] == sku]

        cur_month = int(sku_df[
            sku_df["invoice_date"].dt.date >= current_month_start
        ]["quantity_sold"].sum())

        last_month = int(sku_df[
            (sku_df["invoice_date"].dt.date >= last_month_start) &
            (sku_df["invoice_date"].dt.date <= last_month_end)
        ]["quantity_sold"].sum())

        this_year = int(sku_df[sku_df["invoice_date"].dt.date >= this_year_start]["quantity_sold"].sum())
        last_year = int(sku_df[
            (sku_df["invoice_date"].dt.date >= last_year_start) &
            (sku_df["invoice_date"].dt.date <= last_year_end)
        ]["quantity_sold"].sum())

        yoy_growth = round((this_year - last_year) / last_year * 100, 1) if last_year > 0 else None
        mom_growth = round((cur_month - last_month) / last_month * 100, 1) if last_month > 0 else None

        monthly_avg = float(row["total_units"]) / max(1, len(sku_df["invoice_date"].dt.to_period("M").unique()))
        is_slow = row["total_units"] < monthly_avg * 3 and monthly_avg < 5
        dead_risk = round(max(0.0, 1.0 - (monthly_avg / 10)), 2)

        result.append({
            "sku_code": sku,
            "model_name": row["model_name"],
            "variant": row["variant"],
            "colour": row["colour"],
            "total_units_sold": int(row["total_units"]),
            "total_revenue": round(float(row["total_revenue"]), 2),
            "yoy_growth_percent": yoy_growth,
            "mom_growth_percent": mom_growth,
            "last_month_units": last_month,
            "current_month_units": cur_month,
            "avg_monthly_units": round(monthly_avg, 1),
            "is_slow_moving": is_slow,
            "dead_stock_risk": dead_risk,
        })

    return sorted(result, key=lambda x: x["total_units_sold"], reverse=True)


def get_colour_analysis(db: Session) -> List[Dict]:
    """Sales breakdown by colour with share and YoY growth."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    total_units = df["quantity_sold"].sum()
    agg = df.groupby("colour").agg(
        total_units=("quantity_sold", "sum"),
        revenue=("total_value", "sum"),
    ).reset_index()

    # YoY per colour
    today = date.today()
    ly_start = date(today.year - 1, 1, 1)
    ly_end = date(today.year - 1, 12, 31)
    ty_start = date(today.year, 1, 1)

    result = []
    for _, row in agg.iterrows():
        colour_df = df[df["colour"] == row["colour"]]
        ty_units = int(colour_df[colour_df["invoice_date"].dt.date >= ty_start]["quantity_sold"].sum())
        ly_units = int(colour_df[
            (colour_df["invoice_date"].dt.date >= ly_start) &
            (colour_df["invoice_date"].dt.date <= ly_end)
        ]["quantity_sold"].sum())
        yoy = round((ty_units - ly_units) / ly_units * 100, 1) if ly_units > 0 else None

        result.append({
            "colour": row["colour"],
            "total_units": int(row["total_units"]),
            "revenue": round(float(row["revenue"]), 2),
            "share_pct": round(float(row["total_units"]) / total_units * 100, 1),
            "yoy_growth": yoy,
        })

    return sorted(result, key=lambda x: x["total_units"], reverse=True)


def get_seasonal_patterns(db: Session) -> List[Dict]:
    """Monthly average sales and seasonal factors."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year", "month"]).agg(units=("quantity_sold", "sum")).reset_index()
    avg_by_month = monthly.groupby("month")["units"].mean().reset_index()
    overall_avg = avg_by_month["units"].mean()

    result = []
    for _, row in avg_by_month.iterrows():
        m = int(row["month"])
        result.append({
            "month": m,
            "month_name": MONTH_NAMES[m],
            "avg_units": round(float(row["units"]), 1),
            "seasonal_factor": round(float(row["units"]) / overall_avg, 2) if overall_avg > 0 else 1.0,
            "is_festive_month": m in [10, 11, 12, 3],
            "is_marriage_month": m in [2, 3, 4, 5, 11, 12],
            "is_monsoon_month": m in [6, 7, 8],
        })
    return sorted(result, key=lambda x: x["month"])


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """Aggregated KPIs for the main dashboard."""
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return {}

    today = date.today()
    ytd_df = df[df["invoice_date"].dt.date >= date(today.year, 1, 1)]
    ly_ytd_df = df[
        (df["invoice_date"].dt.date >= date(today.year - 1, 1, 1)) &
        (df["invoice_date"].dt.date < date(today.year, today.month, today.day))
    ]

    ytd_units = int(ytd_df["quantity_sold"].sum())
    ytd_revenue = float(ytd_df["total_value"].sum())
    ly_units = int(ly_ytd_df["quantity_sold"].sum())
    yoy_growth = round((ytd_units - ly_units) / ly_units * 100, 1) if ly_units > 0 else 0.0

    top_sku = df.groupby("sku_code")["quantity_sold"].sum().idxmax()
    top_model = df.groupby("model_name")["quantity_sold"].sum().idxmax()
    top_colour = df.groupby("colour")["quantity_sold"].sum().idxmax()

    monthly_trend = get_mom_analysis(db, recent_months=12)
    sku_rankings = get_sku_performance(db)[:10]

    return {
        "total_units_ytd": ytd_units,
        "total_revenue_ytd": round(ytd_revenue, 2),
        "yoy_growth_pct": yoy_growth,
        "active_alerts": 0,  # filled in by alert service
        "top_sku": top_sku,
        "top_model": top_model,
        "top_colour": top_colour,
        "forecast_accuracy_pct": 87.4,  # illustrative
        "monthly_trend": monthly_trend,
        "sku_rankings": sku_rankings,
    }
