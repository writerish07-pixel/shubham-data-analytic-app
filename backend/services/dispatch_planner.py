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

from models import HeroSalesData
from services.forecasting import run_full_forecast, _sales_df
from services.festival_calendar import get_upcoming_festivals

# Company lead time (days from dispatch order to stock arrival)
DEFAULT_LEAD_TIME = 21
BUFFER_PCT = 0.15  # 15% buffer stock on top of forecast


def _sku_current_stock(db: Session) -> Dict[str, int]:
    """
    Simulate current stock levels based on recent sales velocity.
    In production, this would be an actual stock lookup.
    """
    df = _sales_df(db)
    if df.empty:
        return {}

    # Simulate current stock as 30-day avg * 1.2 (reasonable assumption)
    today = pd.Timestamp.today()
    recent = df[df["invoice_date"] >= today - pd.Timedelta(days=30)]
    monthly_velocity = recent.groupby("sku_code")["quantity_sold"].sum()
    stock = {sku: max(2, int(units * 1.2)) for sku, units in monthly_velocity.items()}
    return stock


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

    # Coverage window
    start = pd.Timestamp.today()
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

        recommendations.append({
            "sku_code": sku,
            "model_name": model,
            "variant": variant,
            "colour": colour,
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
