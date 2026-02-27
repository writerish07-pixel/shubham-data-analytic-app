"""
Predictive Forecasting Engine
Uses seasonal-trend decomposition + festival adjustment.
Falls back gracefully when heavy ML libs (Prophet) are unavailable.
"""
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from models import HeroSalesData, ForecastData
from services.festival_calendar import get_festival_multiplier, MONTHLY_SEASONAL_FACTORS

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


def _sales_df(db: Session) -> pd.DataFrame:
    records = db.query(HeroSalesData).all()
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
    } for r in records]
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["year"] = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    return df


def _sku_base_stats(sku_df: pd.DataFrame) -> Dict:
    """Compute base daily average and YoY trend for a single SKU."""
    if sku_df.empty:
        return {"daily_avg": 0.5, "trend_factor": 1.0, "price": 0}

    # Daily average (units per day)
    total_days = max(1, (sku_df["invoice_date"].max() - sku_df["invoice_date"].min()).days + 1)
    daily_avg = sku_df["quantity_sold"].sum() / total_days

    # YoY trend: slope of annual totals
    annual = sku_df.groupby("year")["quantity_sold"].sum().reset_index()
    trend_factor = 1.07  # default 7% YoY growth
    if len(annual) >= 2:
        years = annual["year"].values.astype(float)
        units = annual["quantity_sold"].values.astype(float)
        if years[-1] != years[0]:
            slope = (units[-1] - units[0]) / (years[-1] - years[0])
            trend_factor = 1.0 + slope / max(1, units[0])

    avg_price = float(sku_df["unit_price"].mean()) if not sku_df.empty else 0.0
    return {"daily_avg": float(daily_avg), "trend_factor": float(trend_factor), "price": avg_price}


def forecast_sku(
    sku_df: pd.DataFrame,
    sku_meta: Dict,
    start_date: date,
    horizon_days: int = 60,
) -> List[Dict]:
    """
    Generate a day-by-day forecast for one SKU.
    Algorithm:
        quantity = daily_avg * seasonal_factor * festival_multiplier * trend_multiplier
    Confidence intervals widen with forecast horizon.
    """
    stats = _sku_base_stats(sku_df)
    daily_avg = stats["daily_avg"]
    trend_factor = min(1.3, max(0.8, stats["trend_factor"]))  # clip extremes

    # Annual trend multiplier relative to today
    current_year = date.today().year
    years_ahead_base = 0  # we predict for near future

    forecast = []
    for d in range(horizon_days):
        target = start_date + timedelta(days=d)
        month = target.month
        seasonal = MONTHLY_SEASONAL_FACTORS.get(month, 1.0)

        # Linear trend ramp over forecast window
        year_fraction = d / 365.0
        trend_mult = 1.0 + (trend_factor - 1.0) * year_fraction

        festival_mult, festival_name = get_festival_multiplier(target)

        predicted = daily_avg * seasonal * trend_mult * festival_mult

        # Confidence intervals grow with horizon
        ci_spread = 0.20 + (d / horizon_days) * 0.15  # 20%–35%
        lower = max(0.0, predicted * (1.0 - ci_spread))
        upper = predicted * (1.0 + ci_spread)

        forecast.append({
            "forecast_date": target,
            "sku_code": sku_meta["sku_code"],
            "model_name": sku_meta["model_name"],
            "variant": sku_meta["variant"],
            "colour": sku_meta["colour"],
            "predicted_quantity": round(predicted, 2),
            "confidence_lower": round(lower, 2),
            "confidence_upper": round(upper, 2),
            "festival_boost": round(festival_mult, 3),
            "festival_name": festival_name or "",
            "forecast_method": "seasonal_trend",
        })
    return forecast


def run_full_forecast(db: Session, horizon_days: int = 60) -> List[Dict]:
    """Run forecast for ALL SKUs and return aggregated results."""
    df = _sales_df(db)
    if df.empty:
        return []

    start_date = date.today()
    skus = df[["sku_code", "model_name", "variant", "colour"]].drop_duplicates()

    all_forecasts = []
    for _, meta in skus.iterrows():
        sku_df = df[df["sku_code"] == meta["sku_code"]]
        fc = forecast_sku(sku_df, meta.to_dict(), start_date, horizon_days)
        all_forecasts.extend(fc)

    return all_forecasts


def get_forecast_summary(db: Session, horizon_days: int = 60) -> List[Dict]:
    """Return per-SKU 30-day and 60-day forecast totals."""
    forecasts = run_full_forecast(db, horizon_days)
    if not forecasts:
        return []

    fc_df = pd.DataFrame(forecasts)
    fc_df["forecast_date"] = pd.to_datetime(fc_df["forecast_date"])
    today = pd.Timestamp.today()
    next30 = today + pd.Timedelta(days=30)

    grouped = fc_df.groupby(["sku_code", "model_name", "variant", "colour"])

    result = []
    for (sku, model, variant, colour), grp in grouped:
        total_60 = grp["predicted_quantity"].sum()
        total_30 = grp[grp["forecast_date"] <= next30]["predicted_quantity"].sum()
        peak_idx = grp["predicted_quantity"].idxmax()
        peak_day = grp.loc[peak_idx, "forecast_date"].date() if pd.notna(peak_idx) else None
        max_boost = grp["festival_boost"].max()
        festival_impact = "High" if max_boost > 1.3 else "Medium" if max_boost > 1.1 else "Low"

        result.append({
            "sku_code": sku,
            "model_name": model,
            "variant": variant,
            "colour": colour,
            "total_forecast_30d": round(float(total_30), 1),
            "total_forecast_60d": round(float(total_60), 1),
            "peak_day": peak_day,
            "festival_impact": festival_impact,
        })
    return sorted(result, key=lambda x: x["total_forecast_60d"], reverse=True)


def what_if_simulation(
    db: Session,
    scenario: str,
    parameter: float,
    sku_codes: Optional[List[str]] = None,
) -> Dict:
    """
    Simulate demand change for various what-if scenarios.
    Scenarios: diwali_shift | fuel_price | competitor_launch | marriage_season
    """
    forecasts = run_full_forecast(db, horizon_days=60)
    if not forecasts:
        return {}

    fc_df = pd.DataFrame(forecasts)
    if sku_codes:
        fc_df = fc_df[fc_df["sku_code"].isin(sku_codes)]

    baseline_units = fc_df["predicted_quantity"].sum()

    if scenario == "diwali_shift":
        # Shift festival dates by N days – impacts seasonal distribution
        shift_days = int(parameter)
        # If Diwali shifts earlier, demand pulls forward
        adjustment = 1.0 + (shift_days / 30) * 0.05
        adjusted_units = baseline_units * adjustment
        notes = f"Diwali shifted {'+' if shift_days > 0 else ''}{shift_days} days → demand pull {'forward' if shift_days < 0 else 'later'}"

    elif scenario == "fuel_price":
        # +1% fuel price ≈ -0.3% two-wheeler demand (price-sensitive market)
        pct_change = parameter  # e.g. 5 = +5%
        demand_effect = -pct_change * 0.3 / 100
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = f"Fuel price +{pct_change}% → estimated demand change: {round(demand_effect*100,1)}%"

    elif scenario == "competitor_launch":
        # Competitor launch reduces demand by impact_score*10%
        impact_score = parameter  # 0–1
        demand_effect = -impact_score * 0.12
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = f"Competitor launch (impact {impact_score}) → estimated demand drop: {round(-demand_effect*100,1)}%"

    elif scenario == "marriage_season":
        # Extended marriage season: +N more muhurat days
        extra_days = int(parameter)
        demand_effect = extra_days * 0.015
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = f"{extra_days} extra marriage muhurat days → uplift: {round(demand_effect*100,1)}%"

    else:
        adjusted_units = baseline_units
        notes = "Unknown scenario"

    delta = adjusted_units - baseline_units
    affected_skus = fc_df["sku_code"].unique().tolist()

    return {
        "scenario": scenario,
        "parameter": parameter,
        "baseline_units": round(float(baseline_units), 1),
        "adjusted_units": round(float(adjusted_units), 1),
        "delta_units": round(float(delta), 1),
        "delta_pct": round(float(delta / baseline_units * 100), 1) if baseline_units > 0 else 0.0,
        "affected_skus": affected_skus[:20],
        "notes": notes,
    }
