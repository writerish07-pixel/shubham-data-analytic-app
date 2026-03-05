"""
Dispatch Planning Engine
Generates SKU-wise dispatch recommendations with risk scoring and
working-capital simulation.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from models import HeroSalesData, StockInventory
from services.forecasting import run_full_forecast, _sales_df
from services.festival_calendar import get_upcoming_festivals

# Company lead time (days from dispatch order to stock arrival)
DEFAULT_LEAD_TIME = 21
BUFFER_PCT = 0.15  # 15% buffer stock on top of forecast


def _sku_current_stock(db: Session) -> Dict[str, int]:
    """
    Return current stock levels from StockInventory table (uploaded by user).
    Falls back to simulated values if no inventory has been uploaded.
    """
    inventory_items = db.query(StockInventory).all()
    if inventory_items:
        # Use real uploaded stock data – aggregate by sku_code
        stock: Dict[str, int] = {}
        for item in inventory_items:
            stock[item.sku_code] = stock.get(item.sku_code, 0) + item.current_stock
        return stock

    # Fallback: estimate stock as 30-day sales * 1.2
    df = _sales_df(db)
    if df.empty:
        return {}
    today = pd.Timestamp.today()
    recent = df[df["invoice_date"] >= today - pd.Timedelta(days=30)]
    monthly_velocity = recent.groupby("sku_code")["quantity_sold"].sum()
    return {sku: max(2, int(units * 1.2)) for sku, units in monthly_velocity.items()}


def _risk_score(
    forecast_units: float,
    current_stock: int,
    lead_time_days: int,
    festival_boost: float,
) -> tuple:
    """
    Returns (risk_score: float 0–1, risk_type: str).
    """
    if forecast_units <= 0:
        return 0.0, "neutral"

    stockout_prob = max(0.0, (forecast_units - current_stock) / forecast_units)
    overstock_prob = max(0.0, (current_stock - forecast_units) / max(1, current_stock))
    volatility = 0.2  # base demand volatility
    festival_risk = max(0.0, (festival_boost - 1.0) * 0.5)  # festival increases understock risk

    score = (
        0.40 * (stockout_prob - overstock_prob) +
        0.30 * stockout_prob +
        0.20 * overstock_prob +
        0.10 * festival_risk
    )
    score = max(0.0, min(1.0, abs(score)))

    if overstock_prob > 0.35:
        risk_type = "overstock"
    elif stockout_prob > 0.30 or festival_boost > 1.25:
        risk_type = "understock"
    else:
        risk_type = "neutral"

    return round(score, 3), risk_type


def generate_dispatch_recommendations(
    db: Session,
    lead_time_days: int = DEFAULT_LEAD_TIME,
) -> List[Dict]:
    """
    Main dispatch planner:
    1. Get 60-day SKU forecasts.
    2. Estimate current stock.
    3. Compute required dispatch quantity.
    4. Score risk.
    5. Output actionable recommendations.
    """
    # Get forecast for the next (lead_time + 30) days coverage window
    coverage_days = lead_time_days + 30
    forecasts = run_full_forecast(db, horizon_days=coverage_days)
    if not forecasts:
        return []

    fc_df = pd.DataFrame(forecasts)
    fc_df["forecast_date"] = pd.to_datetime(fc_df["forecast_date"])
    # Fill NaN in groupby key columns to avoid silent row drops
    for col in ["sku_code", "model_name", "variant", "colour"]:
        if col in fc_df.columns:
            fc_df[col] = fc_df[col].fillna("").astype(str)

    # Coverage window — use date-only comparison to avoid time-of-day filtering
    start = pd.Timestamp(date.today())
    end = start + pd.Timedelta(days=coverage_days)

    current_stock_map = _sku_current_stock(db)
    upcoming_festivals = get_upcoming_festivals(days_ahead=60)
    max_festival_boost = max([1.0] + [1.0 + f["impact_pct"]/100 for f in upcoming_festivals[:1]])

    # SKU-level aggregation
    sku_groups = fc_df.groupby(["sku_code", "model_name", "variant", "colour"])
    recommendations = []
    today_date = date.today()

    for (sku, model, variant, colour), grp in sku_groups:
        window = grp[(grp["forecast_date"] >= start) & (grp["forecast_date"] <= end)]
        forecast_units = float(window["predicted_quantity"].sum())
        peak_festival_boost = float(window["festival_boost"].max())

        current_stock = current_stock_map.get(sku, 0)
        buffer = int(np.ceil(forecast_units * BUFFER_PCT))
        required = max(0, int(np.ceil(forecast_units)) - current_stock + buffer)

        risk, risk_type = _risk_score(forecast_units, current_stock, lead_time_days, peak_festival_boost)

        # Estimate avg unit price from recent sales
        sales_df = _sales_df(db)
        sku_price = float(
            sales_df[sales_df["sku_code"] == sku]["unit_price"].mean()
            if not sales_df.empty and sku in sales_df["sku_code"].values
            else 0
        )
        wc_impact = required * sku_price

        notes_parts = []
        if peak_festival_boost > 1.2:
            notes_parts.append(f"Festival demand boost expected ({round((peak_festival_boost-1)*100)}% uplift)")
        if risk_type == "understock":
            notes_parts.append("⚠️ Risk of stockout – order urgently")
        if risk_type == "overstock":
            notes_parts.append("📦 Current stock may be sufficient – consider reducing dispatch")

        stock_source = "uploaded" if db.query(StockInventory).first() else "estimated"
        recommendations.append({
            "sku_code": sku,
            "model_name": model,
            "variant": variant,
            "colour": colour,
            "current_stock": current_stock,
            "stock_source": stock_source,
            "forecast_units": round(forecast_units, 0),
            "recommended_quantity": required,
            "buffer_stock": buffer,
            "total_dispatch": required,
            "risk_score": risk,
            "risk_type": risk_type,
            "working_capital_impact": round(wc_impact, 2),
            "festival_factor": round(peak_festival_boost, 2),
            "unit_price": round(sku_price, 2),
            "notes": " | ".join(notes_parts) if notes_parts else "Normal dispatch recommended",
        })

    return sorted(recommendations, key=lambda x: x["risk_score"], reverse=True)


# ─── Target-based dispatch ────────────────────────────────────────────────────

_MONTH_NAMES = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
]


def _model_stock_map(db: Session) -> Dict[str, int]:
    """Return total current stock aggregated by model_name from uploaded inventory."""
    items = db.query(StockInventory).all()
    stock: Dict[str, int] = {}
    for item in items:
        name = (item.model_name or item.sku_code or "").strip()
        if name:
            stock[name] = stock.get(name, 0) + item.current_stock
    return stock


def _find_model_stock(model_stock: Dict[str, int], model_name: str) -> int:
    """Match model to stock with exact then partial name matching."""
    if model_name in model_stock:
        return model_stock[model_name]
    low = model_name.lower()
    total = 0
    for k, v in model_stock.items():
        if low in k.lower() or k.lower() in low:
            total += v
    return total


def _model_velocity(df: pd.DataFrame, model_name: str, days: int = 30) -> float:
    """Daily sales velocity for a model over the last N days of data."""
    if df.empty:
        return 0.0
    latest = df["invoice_date"].max()
    cutoff = latest - pd.Timedelta(days=days)
    recent = df[(df["invoice_date"] >= cutoff) & (df["model_name"] == model_name)]
    return float(recent["quantity_sold"].sum()) / max(1, days)


def _dispatch_notes(risk_type: str, festival_boost: float, festivals: list) -> str:
    parts = []
    if festival_boost > 1.05:
        names = ", ".join(f["name"] for f in festivals[:2])
        parts.append(f"Festival boost +{round((festival_boost - 1) * 100)}% ({names})")
    if risk_type == "understock":
        parts.append("⚠️ Low stock — order urgently")
    elif risk_type == "overstock":
        parts.append("📦 Sufficient stock — verify before ordering")
    return " | ".join(parts) if parts else "Normal order"


def generate_target_based_dispatch(db: Session, year: int, month: int) -> Dict[str, Any]:
    """
    Dispatch plan driven by monthly sales target, not historical forecast.

    For each model:
      order_qty = max(0, festival_adjusted_remaining - current_stock + 15% buffer)

    If model-wise targets are set → uses them directly.
    Otherwise distributes the overall target by 3-month historical sales mix.
    """
    import calendar as _cal
    from services.target_engine import get_targets_for_month, compute_auto_target

    # 1. Targets
    tdata        = get_targets_for_month(db, year, month)
    overall_data = tdata.get("overall") or {}
    model_targets = tdata.get("model_targets") or []
    has_model_targets = tdata.get("has_model_targets", False)

    overall_units = overall_data.get("target_units") or 0
    is_manual     = overall_data.get("is_manual", False)
    if not overall_units:
        auto = compute_auto_target(db, year, month)
        overall_units = auto.get("target_units", 0)
        is_manual = False

    # 2. Festivals in target month
    month_start     = date(year, month, 1)
    days_in_month   = _cal.monthrange(year, month)[1]
    month_festivals = get_upcoming_festivals(from_date=month_start, days_ahead=days_in_month)
    festival_boost  = max([1.0] + [1.0 + f["impact_pct"] / 100 for f in month_festivals])

    # 3. Stock data
    model_stock  = _model_stock_map(db)
    stock_source = "uploaded" if db.query(StockInventory).first() else "estimated"
    df           = _sales_df(db)

    plans = []

    if has_model_targets and model_targets:
        for mt in model_targets:
            name      = mt["model_name"]
            target    = mt["target_units"]
            sold      = mt.get("actuals_so_far", 0)
            remaining = mt.get("remaining", target)

            curr   = _find_model_stock(model_stock, name)
            adj    = int(np.ceil(remaining * festival_boost))
            buffer = int(np.ceil(adj * BUFFER_PCT))
            order  = max(0, adj - curr + buffer)

            risk, rtype = _risk_score(adj, curr, DEFAULT_LEAD_TIME, festival_boost)

            plans.append({
                "model_name":        name,
                "monthly_target":    target,
                "already_sold":      sold,
                "remaining_target":  remaining,
                "current_stock":     curr,
                "stock_source":      stock_source,
                "daily_velocity":    round(_model_velocity(df, name), 1),
                "festival_adjusted": adj,
                "buffer_stock":      buffer,
                "order_quantity":    order,
                "risk_score":        round(risk, 3),
                "risk_type":         rtype,
                "festival_factor":   round(festival_boost, 2),
                "notes":             _dispatch_notes(rtype, festival_boost, month_festivals),
                "source":            "model_target",
            })

    elif not df.empty and overall_units > 0:
        # Distribute by 3-month mix
        latest  = df["invoice_date"].max()
        cutoff  = latest - pd.Timedelta(days=90)
        recent  = df[df["invoice_date"] >= cutoff]
        mix     = recent.groupby("model_name")["quantity_sold"].sum()
        total_m = float(mix.sum())

        for name, mu in mix.sort_values(ascending=False).items():
            share  = float(mu) / total_m if total_m > 0 else 0
            target = max(1, int(round(overall_units * share)))

            curr   = _find_model_stock(model_stock, name)
            adj    = int(np.ceil(target * festival_boost))
            buffer = int(np.ceil(adj * BUFFER_PCT))
            order  = max(0, adj - curr + buffer)

            risk, rtype = _risk_score(adj, curr, DEFAULT_LEAD_TIME, festival_boost)

            plans.append({
                "model_name":        name,
                "monthly_target":    target,
                "already_sold":      0,
                "remaining_target":  target,
                "current_stock":     curr,
                "stock_source":      stock_source,
                "daily_velocity":    round(_model_velocity(df, name), 1),
                "festival_adjusted": adj,
                "buffer_stock":      buffer,
                "order_quantity":    order,
                "risk_score":        round(risk, 3),
                "risk_type":         rtype,
                "festival_factor":   round(festival_boost, 2),
                "mix_pct":           round(share * 100, 1),
                "notes":             _dispatch_notes(rtype, festival_boost, month_festivals),
                "source":            "auto_distributed",
            })
        plans.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "target_month":       _MONTH_NAMES[month - 1],
        "target_year":        year,
        "overall_target":     overall_units,
        "is_manual_target":   is_manual,
        "has_model_targets":  has_model_targets,
        "stock_source":       stock_source,
        "festival_boost":     round(festival_boost, 2),
        "festivals_this_month": [
            {"name": f["name"], "date": str(f["date"]), "impact_pct": f["impact_pct"]}
            for f in month_festivals
        ],
        "model_plans": plans,
        "summary": {
            "total_order_quantity":  sum(p["order_quantity"] for p in plans),
            "total_current_stock":   sum(p["current_stock"] for p in plans),
            "models_at_risk":        len([p for p in plans if p["risk_type"] == "understock"]),
            "models_overstocked":    len([p for p in plans if p["risk_type"] == "overstock"]),
            "models_ok":             len([p for p in plans if p["risk_type"] == "neutral"]),
        },
    }


def generate_sku_stock_plan(db: Session, year: int, month: int) -> Dict[str, Any]:
    """
    SKU-level stock order plan based on monthly sales target.

    Formula (per SKU):
      daily_rate          = sku_target / 30
      stock_after_sales   = current_stock - sku_target
      min_buffer_needed   = daily_rate × 30  (30-day minimum buffer)
      max_buffer_needed   = daily_rate × 45  (45-day recommended buffer)
      order_qty_min       = max(0, min_buffer_needed - stock_after_sales)
                          = max(0, 2 × sku_target - current_stock)
      order_qty_max       = max(0, max_buffer_needed - stock_after_sales)
                          = max(0, 2.5 × sku_target - current_stock)
    """
    import calendar as _cal
    import math as _math
    from services.target_engine import get_sku_targets

    # Get SKU-level targets
    sku_data = get_sku_targets(db, year, month)
    sku_targets_list = sku_data.get("sku_targets", [])
    overall_target = sku_data.get("overall_target", 0)

    # Festivals in target month
    month_start   = date(year, month, 1)
    days_in_month = _cal.monthrange(year, month)[1]
    month_festivals = get_upcoming_festivals(from_date=month_start, days_ahead=days_in_month)
    festival_boost  = max([1.0] + [1.0 + f["impact_pct"] / 100 for f in month_festivals])

    # Get stock from uploaded inventory or estimate from sales
    stock_items = db.query(StockInventory).all()
    stock_source = "uploaded" if stock_items else "estimated"
    sku_stock_map: Dict[str, int] = {}
    if stock_items:
        for item in stock_items:
            sku_stock_map[item.sku_code] = sku_stock_map.get(item.sku_code, 0) + item.current_stock
    else:
        # Estimate from recent sales velocity
        df = _sales_df(db)
        if not df.empty:
            if "sku_code" not in df.columns and "colour" in df.columns:
                df["sku_code"] = df["model_name"] + "_" + df["colour"].fillna("DEFAULT")
            latest = df["invoice_date"].max()
            recent = df[df["invoice_date"] >= latest - pd.Timedelta(days=30)]
            vel = recent.groupby("sku_code")["quantity_sold"].sum()
            sku_stock_map = {s: max(2, int(u * 1.2)) for s, u in vel.items()}

    plans = []
    for sku in sku_targets_list:
        sku_code    = sku["sku_code"]
        sku_target  = sku["target_units"]
        current_stk = sku_stock_map.get(sku_code, 0)
        daily_rate  = round(sku_target / 30, 2)

        # Stock remaining after selling this month's target
        stock_after_sales = current_stk - sku_target

        # Buffer stock needed to maintain 30 / 45 days of cover after sales
        min_buffer = sku_target          # daily_rate × 30 = target
        max_buffer = _math.ceil(sku_target * 1.5)  # daily_rate × 45

        order_min = max(0, min_buffer - stock_after_sales)
        order_max = max(0, max_buffer - stock_after_sales)

        # Days of stock after selling target
        days_cover_after = int(stock_after_sales / daily_rate) if daily_rate > 0 and stock_after_sales > 0 else 0

        if stock_after_sales < 0:
            status = "critical"   # not enough stock to even cover sales target
            notes  = "⚠️ Current stock insufficient for sales target — order immediately"
        elif days_cover_after < 30:
            status = "low"
            notes  = f"Only {days_cover_after}d stock remains after target sales — order to maintain 30d buffer"
        elif days_cover_after <= 45:
            status = "ok"
            notes  = f"{days_cover_after}d stock buffer after sales — within 30-45d range"
        else:
            status = "excess"
            notes  = f"{days_cover_after}d stock buffer — above 45d; consider reducing order"

        plans.append({
            "sku_code":          sku_code,
            "model_name":        sku["model_name"],
            "colour":            sku["colour"],
            "monthly_target":    sku_target,
            "current_stock":     current_stk,
            "stock_source":      stock_source,
            "daily_rate":        daily_rate,
            "stock_after_sales": stock_after_sales,
            "days_cover_after_sales": days_cover_after,
            "min_buffer_30d":    min_buffer,
            "max_buffer_45d":    max_buffer,
            "order_qty_min":     order_min,
            "order_qty_max":     order_max,
            "order_qty":         order_min,   # recommended = 30-day minimum
            "festival_boost":    round(festival_boost, 2),
            "status":            status,
            "notes":             notes,
        })

    status_order = {"critical": 0, "low": 1, "ok": 2, "excess": 3}
    plans.sort(key=lambda x: status_order.get(x["status"], 9))

    return {
        "target_month":    _MONTH_NAMES[month - 1],
        "target_year":     year,
        "overall_target":  overall_target,
        "stock_source":    stock_source,
        "has_model_targets": sku_data.get("has_model_targets", False),
        "festival_boost":  round(festival_boost, 2),
        "festivals_this_month": [
            {"name": f["name"], "date": str(f["date"]), "impact_pct": f["impact_pct"]}
            for f in month_festivals
        ],
        "sku_plans": plans,
        "summary": {
            "total_skus":          len(plans),
            "total_order_min":     sum(p["order_qty_min"] for p in plans),
            "total_order_max":     sum(p["order_qty_max"] for p in plans),
            "total_current_stock": sum(p["current_stock"] for p in plans),
            "critical_count":      len([p for p in plans if p["status"] == "critical"]),
            "low_count":           len([p for p in plans if p["status"] == "low"]),
            "ok_count":            len([p for p in plans if p["status"] == "ok"]),
            "excess_count":        len([p for p in plans if p["status"] == "excess"]),
        },
    }


def stock_health_analysis(db: Session, year: int, month: int) -> Dict[str, Any]:
    """
    Compare current stock vs what is needed for the given month's target.
    Returns model-wise health status: critical / low / ok / excess.
    """
    from services.target_engine import get_targets_for_month, compute_auto_target

    tdata         = get_targets_for_month(db, year, month)
    overall_data  = tdata.get("overall") or {}
    model_targets = tdata.get("model_targets") or []
    has_model_targets = tdata.get("has_model_targets", False)

    overall_units = overall_data.get("target_units") or 0
    if not overall_units:
        auto = compute_auto_target(db, year, month)
        overall_units = auto.get("target_units", 0)

    model_stock  = _model_stock_map(db)
    df           = _sales_df(db)
    stock_source = "uploaded" if db.query(StockInventory).first() else "no_stock_uploaded"

    def _status(curr: int, needed: int) -> str:
        if needed == 0:
            return "ok"
        r = curr / needed
        if r >= 1.2:   return "excess"
        if r >= 0.8:   return "ok"
        if r >= 0.4:   return "low"
        return "critical"

    items = []

    if has_model_targets and model_targets:
        for mt in model_targets:
            name      = mt["model_name"]
            needed    = mt["target_units"]
            remaining = mt.get("remaining", needed)
            curr      = _find_model_stock(model_stock, name)
            vel       = _model_velocity(df, name)
            days_cov  = int(curr / vel) if vel > 0 else 999

            items.append({
                "model_name":      name,
                "current_stock":   curr,
                "target_needed":   needed,
                "remaining":       remaining,
                "coverage_ratio":  round(curr / needed, 2) if needed > 0 else 0,
                "status":          _status(curr, remaining),
                "daily_velocity":  round(vel, 1),
                "days_of_stock":   min(days_cov, 999),
                "gap":             max(0, remaining - curr),
                "surplus":         max(0, curr - remaining),
                "source":          "model_target",
            })

    elif not df.empty and overall_units > 0:
        latest  = df["invoice_date"].max()
        cutoff  = latest - pd.Timedelta(days=90)
        recent  = df[df["invoice_date"] >= cutoff]
        mix     = recent.groupby("model_name")["quantity_sold"].sum()
        total_m = float(mix.sum())

        for name, mu in mix.sort_values(ascending=False).items():
            share  = float(mu) / total_m if total_m > 0 else 0
            needed = max(1, int(round(overall_units * share)))
            curr   = _find_model_stock(model_stock, name)
            vel    = _model_velocity(df, name)
            days_cov = int(curr / vel) if vel > 0 else 999

            items.append({
                "model_name":      name,
                "current_stock":   curr,
                "target_needed":   needed,
                "remaining":       needed,
                "coverage_ratio":  round(curr / needed, 2) if needed > 0 else 0,
                "status":          _status(curr, needed),
                "daily_velocity":  round(vel, 1),
                "days_of_stock":   min(days_cov, 999),
                "gap":             max(0, needed - curr),
                "surplus":         max(0, curr - needed),
                "source":          "auto_distributed",
            })

    status_order = {"critical": 0, "low": 1, "ok": 2, "excess": 3}
    items.sort(key=lambda x: status_order.get(x["status"], 9))

    return {
        "target_month":    _MONTH_NAMES[month - 1],
        "target_year":     year,
        "overall_target":  overall_units,
        "stock_source":    stock_source,
        "has_stock_data":  bool(model_stock),
        "items":           items,
        "summary": {
            "total_current_stock":  sum(i["current_stock"] for i in items),
            "total_target_needed":  sum(i["target_needed"] for i in items),
            "critical_count":       len([i for i in items if i["status"] == "critical"]),
            "low_count":            len([i for i in items if i["status"] == "low"]),
            "ok_count":             len([i for i in items if i["status"] == "ok"]),
            "excess_count":         len([i for i in items if i["status"] == "excess"]),
        },
    }


def working_capital_summary(db: Session) -> Dict[str, Any]:
    """Compute overall working capital exposure and dead stock risk."""
    recommendations = generate_dispatch_recommendations(db)
    if not recommendations:
        return {}

    total_dispatch_value = sum(r["working_capital_impact"] for r in recommendations)
    total_buffer_value = sum(r["buffer_stock"] * r["unit_price"] for r in recommendations)

    # Overstock = dead stock risk
    overstock = [r for r in recommendations if r["risk_type"] == "overstock"]
    dead_stock_exposure = sum(r["working_capital_impact"] for r in overstock)

    # Average working capital rotation (days inventory outstanding)
    sales_df = _sales_df(db)
    if not sales_df.empty:
        avg_daily_revenue = float(
            (sales_df["quantity_sold"] * sales_df["unit_price"]).sum()
        ) / max(1, (sales_df["invoice_date"].max() - sales_df["invoice_date"].min()).days)
        rotation_days = total_dispatch_value / max(1, avg_daily_revenue)
    else:
        rotation_days = 30.0

    high_risk = [r["sku_code"] for r in recommendations if r["risk_score"] > 0.6]

    return {
        "total_dispatch_value": round(total_dispatch_value, 2),
        "total_buffer_value": round(total_buffer_value, 2),
        "dead_stock_exposure": round(dead_stock_exposure, 2),
        "capital_rotation_days": round(rotation_days, 1),
        "high_risk_skus": high_risk[:10],
        "overstock_count": len(overstock),
        "understock_count": len([r for r in recommendations if r["risk_type"] == "understock"]),
    }
