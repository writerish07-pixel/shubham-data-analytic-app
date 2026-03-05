"""
Sales Analytics Service — fixed + enhanced
Key fixes:
  • get_sku_performance: same-period YoY (Jan-Feb this year vs Jan-Feb last year)
  • Returns ALL SKUs (no limit) — frontend paginates/filters
  • Revenue gracefully shown as 0 when price data missing (frontend labels it N/A)
  • get_model_monthly_trend: per-model monthly breakdown for target pathway
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import pandas as pd

from models import HeroSalesData, SKUPerformance

MONTHLY_SEASONAL_FACTORS = {
    1: 0.85, 2: 0.92, 3: 1.15, 4: 0.95, 5: 1.00,
    6: 0.82, 7: 0.78, 8: 0.95, 9: 1.08,
    10: 1.38, 11: 1.52, 12: 1.22,
}

MONTH_NAMES = {
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec",
}


def _sales_to_df(records) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    rows = [{
        "invoice_date": r.invoice_date,
        "sku_code":     r.sku_code,
        "model_name":   r.model_name,
        "variant":      r.variant,
        "colour":       r.colour,
        "quantity_sold":r.quantity_sold,
        "unit_price":   r.unit_price,
        "total_value":  r.total_value,
        "location":     r.location,
        "region":       r.region,
    } for r in records]
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["year"]  = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    return df


def _get_latest_year(df: pd.DataFrame) -> int:
    if df.empty:
        return date.today().year
    return int(df["year"].max())


def _get_latest_date_in_data(df: pd.DataFrame) -> date:
    if df.empty:
        return date.today()
    return df["invoice_date"].max().date()


# ── data-info ────────────────────────────────────────────────────────────────

def get_data_info(db: Session) -> Dict[str, Any]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return {"has_data": False, "total_records": 0, "date_range_start": None,
                "date_range_end": None, "years_available": [], "total_units": 0,
                "total_revenue": 0, "sku_count": 0, "location_count": 0}

    years     = sorted(df["year"].unique().tolist())
    locations = df["location"].dropna().unique().tolist()
    has_price = bool((df["unit_price"] > 0).any())

    return {
        "has_data":         True,
        "total_records":    len(records),
        "date_range_start": str(df["invoice_date"].min().date()),
        "date_range_end":   str(df["invoice_date"].max().date()),
        "years_available":  [int(y) for y in years],
        "total_units":      int(df["quantity_sold"].sum()),
        "total_revenue":    round(float(df["total_value"].sum()), 2),
        "sku_count":        int(df["sku_code"].nunique()),
        "model_count":      int(df["model_name"].nunique()),
        "location_count":   len(locations),
        "has_price_data":   has_price,
        "top_location":     df.groupby("location")["quantity_sold"].sum().idxmax()
                            if not df["location"].isna().all() else None,
    }


# ── YoY / MoM ────────────────────────────────────────────────────────────────

def get_yoy_analysis(db: Session) -> List[Dict]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year","month"]).agg(
        units=("quantity_sold","sum"), revenue=("total_value","sum")
    ).reset_index()

    result = []
    for _, row in monthly.iterrows():
        prev = monthly[(monthly["year"]==row["year"]-1) & (monthly["month"]==row["month"])]
        gp = None
        if not prev.empty:
            pu = prev.iloc[0]["units"]
            gp = round((row["units"]-pu)/pu*100, 1) if pu > 0 else None
        result.append({
            "year": int(row["year"]), "month": int(row["month"]),
            "month_name": MONTH_NAMES[int(row["month"])],
            "units": int(row["units"]),
            "revenue": round(float(row["revenue"]), 2),
            "growth_pct": gp,
        })
    return sorted(result, key=lambda x: (x["year"], x["month"]))


def get_mom_analysis(db: Session, recent_months: int = 24) -> List[Dict]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year","month"]).agg(
        units=("quantity_sold","sum"), revenue=("total_value","sum")
    ).reset_index().sort_values(["year","month"])
    monthly = monthly.tail(recent_months).reset_index(drop=True)

    result = []
    for i, row in monthly.iterrows():
        mg = None
        if i > 0:
            prev = monthly.iloc[i-1]
            mg = round((row["units"]-prev["units"])/prev["units"]*100,1) if prev["units"]>0 else None
        result.append({
            "year": int(row["year"]), "month": int(row["month"]),
            "month_name": MONTH_NAMES[int(row["month"])],
            "units": int(row["units"]),
            "revenue": round(float(row["revenue"]),2),
            "mom_growth_pct": mg,
        })
    return result


# ── SKU performance (FIXED: same-period YoY, ALL SKUs) ───────────────────────

def get_sku_performance(db: Session) -> List[Dict]:
    """
    Returns performance for ALL SKUs in the uploaded data.
    YoY = same calendar period this year vs same period last year
    (e.g. Jan-Feb 2026 vs Jan-Feb 2025 — apples to apples).
    """
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    latest_year = _get_latest_year(df)
    latest_date = _get_latest_date_in_data(df)

    # Current-month window (latest full month in data)
    cur_month_start = date(latest_year, latest_date.month, 1)
    if latest_date.month > 1:
        prev_month_start = date(latest_year, latest_date.month - 1, 1)
    else:
        prev_month_start = date(latest_year - 1, 12, 1)
    prev_month_end = cur_month_start - timedelta(days=1)

    # Same-period YoY: Jan 1 → latest_date  vs  Jan 1 → same day last year
    ty_start = date(latest_year, 1, 1)
    ty_end   = latest_date
    ly_start = date(latest_year - 1, 1, 1)
    ly_end   = date(latest_year - 1, latest_date.month, latest_date.day)

    # Aggregate by model_name + colour (handles dealer SKU codes that vary)
    agg = df.groupby(["model_name", "colour", "variant"]).agg(
        total_units   =("quantity_sold","sum"),
        total_revenue =("total_value","sum"),
        sku_codes     =("sku_code", lambda x: list(x.unique())),
    ).reset_index()

    has_price = bool((df["unit_price"] > 0).any())

    result = []
    for _, row in agg.iterrows():
        mask = (df["model_name"]==row["model_name"]) & (df["colour"]==row["colour"])
        sub  = df[mask]

        cur_m  = int(sub[sub["invoice_date"].dt.date >= cur_month_start]["quantity_sold"].sum())
        prev_m = int(sub[(sub["invoice_date"].dt.date >= prev_month_start) &
                         (sub["invoice_date"].dt.date <= prev_month_end)]["quantity_sold"].sum())

        ty = int(sub[(sub["invoice_date"].dt.date >= ty_start) &
                     (sub["invoice_date"].dt.date <= ty_end)]["quantity_sold"].sum())
        ly = int(sub[(sub["invoice_date"].dt.date >= ly_start) &
                     (sub["invoice_date"].dt.date <= ly_end)]["quantity_sold"].sum())

        yoy = round((ty-ly)/ly*100, 1) if ly > 0 else None
        mom = round((cur_m-prev_m)/prev_m*100, 1) if prev_m > 0 else None

        periods = len(sub["invoice_date"].dt.to_period("M").unique())
        avg_monthly = float(row["total_units"]) / max(1, periods)
        is_slow  = avg_monthly < 3 and periods >= 3
        dead_risk= round(max(0.0, 1.0 - avg_monthly/10), 2)

        result.append({
            "sku_code":            row["sku_codes"][0] if row["sku_codes"] else "",
            "model_name":          row["model_name"],
            "variant":             row["variant"],
            "colour":              row["colour"],
            "total_units_sold":    int(row["total_units"]),
            "total_revenue":       round(float(row["total_revenue"]),2),
            "has_price_data":      has_price,
            "yoy_growth_percent":  yoy,
            "mom_growth_percent":  mom,
            "last_month_units":    prev_m,
            "current_month_units": cur_m,
            "avg_monthly_units":   round(avg_monthly,1),
            "is_slow_moving":      is_slow,
            "dead_stock_risk":     dead_risk,
            "ref_year":            latest_year,
            "ref_period":          f"{MONTH_NAMES[1]} {latest_year} – {MONTH_NAMES[latest_date.month]} {latest_date.day}, {latest_year}",
            "last_period":         f"{MONTH_NAMES[1]} {latest_year-1} – {MONTH_NAMES[ly_end.month]} {ly_end.day}, {latest_year-1}",
        })

    return sorted(result, key=lambda x: x["total_units_sold"], reverse=True)


def get_colour_analysis(db: Session) -> List[Dict]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    total_units = df["quantity_sold"].sum()
    agg = df.groupby("colour").agg(
        total_units=("quantity_sold","sum"), revenue=("total_value","sum")
    ).reset_index()

    latest_year = _get_latest_year(df)
    latest_date = _get_latest_date_in_data(df)
    ty_start = date(latest_year,1,1)
    ly_start = date(latest_year-1,1,1)
    ly_end   = date(latest_year-1, latest_date.month, latest_date.day)

    result = []
    for _, row in agg.iterrows():
        cd = df[df["colour"]==row["colour"]]
        ty = int(cd[cd["invoice_date"].dt.date>=ty_start]["quantity_sold"].sum())
        ly = int(cd[(cd["invoice_date"].dt.date>=ly_start)&(cd["invoice_date"].dt.date<=ly_end)]["quantity_sold"].sum())
        yoy = round((ty-ly)/ly*100,1) if ly>0 else None
        result.append({
            "colour":      row["colour"],
            "total_units": int(row["total_units"]),
            "revenue":     round(float(row["revenue"]),2),
            "share_pct":   round(float(row["total_units"])/total_units*100,1),
            "yoy_growth":  yoy,
        })
    return sorted(result, key=lambda x: x["total_units"], reverse=True)


def get_seasonal_patterns(db: Session) -> List[Dict]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year","month"]).agg(units=("quantity_sold","sum")).reset_index()
    avg_by_m = monthly.groupby("month")["units"].mean().reset_index()
    overall  = avg_by_m["units"].mean()

    result = []
    for _, row in avg_by_m.iterrows():
        m = int(row["month"])
        result.append({
            "month":           m,
            "month_name":      MONTH_NAMES[m],
            "avg_units":       round(float(row["units"]),1),
            "seasonal_factor": round(float(row["units"])/overall,2) if overall>0 else 1.0,
            "is_festive_month":  m in [10,11,12,3],
            "is_marriage_month": m in [2,3,4,5,11,12],
            "is_monsoon_month":  m in [6,7,8],
        })
    return sorted(result, key=lambda x: x["month"])


def get_location_analysis(db: Session) -> List[Dict]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    latest_year = _get_latest_year(df)
    latest_date = _get_latest_date_in_data(df)
    ty_start = date(latest_year,1,1)
    ly_start = date(latest_year-1,1,1)
    ly_end   = date(latest_year-1, latest_date.month, latest_date.day)

    has_loc = not df["location"].isna().all()
    grp_col = "location" if has_loc else "region"
    loc_df  = df.dropna(subset=[grp_col])
    if loc_df.empty:
        return []

    agg = loc_df.groupby(grp_col).agg(
        total_units=("quantity_sold","sum"), total_revenue=("total_value","sum")
    ).reset_index()
    total = agg["total_units"].sum()

    result = []
    for _, row in agg.iterrows():
        loc = row[grp_col]
        ld  = loc_df[loc_df[grp_col]==loc]
        top_model = ld.groupby("model_name")["quantity_sold"].sum().idxmax() if not ld.empty else "—"
        ty  = int(ld[ld["invoice_date"].dt.date>=ty_start]["quantity_sold"].sum())
        ly  = int(ld[(ld["invoice_date"].dt.date>=ly_start)&(ld["invoice_date"].dt.date<=ly_end)]["quantity_sold"].sum())
        yoy = round((ty-ly)/ly*100,1) if ly>0 else None
        rv  = loc_df[loc_df[grp_col]==loc]["region"].dropna().unique()
        result.append({
            "location":       loc,
            "region":         rv[0] if len(rv)>0 else loc,
            "total_units":    int(row["total_units"]),
            "total_revenue":  round(float(row["total_revenue"]),2),
            "share_pct":      round(float(row["total_units"])/total*100,1),
            "yoy_growth":     yoy,
            "top_model":      top_model,
            "this_year_units":ty,
            "last_year_units":ly,
        })
    return sorted(result, key=lambda x: x["total_units"], reverse=True)


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    records = db.query(HeroSalesData).all()
    df = _sales_to_df(records)
    if df.empty:
        return {}

    latest_year = _get_latest_year(df)
    latest_date = _get_latest_date_in_data(df)

    ytd_start   = date(latest_year, 1, 1)
    ly_ytd_start= date(latest_year-1, 1, 1)
    ly_ytd_end  = date(latest_year-1, latest_date.month, latest_date.day)

    ytd_df  = df[(df["invoice_date"].dt.date>=ytd_start)&(df["invoice_date"].dt.date<=latest_date)]
    ly_df   = df[(df["invoice_date"].dt.date>=ly_ytd_start)&(df["invoice_date"].dt.date<=ly_ytd_end)]

    ytd_units   = int(ytd_df["quantity_sold"].sum())
    ytd_revenue = float(ytd_df["total_value"].sum())
    ly_units    = int(ly_df["quantity_sold"].sum())
    yoy_growth  = round((ytd_units-ly_units)/ly_units*100,1) if ly_units>0 else 0.0

    top_sku    = df.groupby("sku_code")["quantity_sold"].sum().idxmax()
    top_model  = df.groupby("model_name")["quantity_sold"].sum().idxmax()
    top_colour = df.groupby("colour")["quantity_sold"].sum().idxmax()

    return {
        "total_units_ytd":    ytd_units,
        "total_revenue_ytd":  round(ytd_revenue,2),
        "yoy_growth_pct":     yoy_growth,
        "active_alerts":      0,
        "top_sku":            top_sku,
        "top_model":          top_model,
        "top_colour":         top_colour,
        "forecast_accuracy_pct": _compute_forecast_accuracy(db),
        "monthly_trend":      get_mom_analysis(db, recent_months=12),
        "sku_rankings":       get_sku_performance(db)[:10],
        "ref_year":           latest_year,
        "data_range_start":   str(df["invoice_date"].min().date()),
        "data_range_end":     str(latest_date),
        "has_price_data":     bool((df["unit_price"]>0).any()),
    }


def _compute_forecast_accuracy(db: Session) -> Optional[float]:
    """Lazy-import forecast accuracy to avoid circular import."""
    try:
        from services.forecasting import compute_forecast_accuracy
        result = compute_forecast_accuracy(db)
        return result.get("accuracy_pct")
    except Exception:
        return None


def get_model_monthly_history(db: Session, model_name: str) -> List[Dict]:
    """
    Monthly sales history for a single model — used by target pathway engine.
    """
    records = db.query(HeroSalesData).filter(
        HeroSalesData.model_name == model_name
    ).all()
    df = _sales_to_df(records)
    if df.empty:
        return []

    monthly = df.groupby(["year","month"]).agg(
        units=("quantity_sold","sum"),revenue=("total_value","sum")
    ).reset_index().sort_values(["year","month"])

    return [{
        "year":        int(r["year"]),
        "month":       int(r["month"]),
        "month_name":  MONTH_NAMES[int(r["month"])],
        "units":       int(r["units"]),
        "revenue":     round(float(r["revenue"]),2),
    } for _, r in monthly.iterrows()]


def get_all_model_names(db: Session) -> List[str]:
    """Return unique model names sorted alphabetically."""
    records = db.query(HeroSalesData.model_name).distinct().all()
    return sorted([r[0] for r in records])
