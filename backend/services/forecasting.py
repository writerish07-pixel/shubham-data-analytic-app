"""
Predictive Forecasting Engine — Data-Anchored
═══════════════════════════════════════════════════════════════════════════
Core forecasting logic (data-first, fallback to market priors):

  For each forecast day (month M of year Y):
    1. LYSM anchor: use last-year-same-month (Y-1, M) daily rate × YoY trend
    2. If no LYSM data: use average of all historical months-M across years × trend
    3. If no month-M data: use overall daily avg × data-derived seasonal factor
    4. Multiply by: festival multiplier + marriage muhurtat boost

  The seasonal factor table is built from the actual uploaded sales data,
  so October peaks in your data drive October forecasts — not generic market priors.

Market context applied:
  • Festival calendar (Diwali, Dhanteras, Akshaya Tritiya, Navratri, Onam…)
  • Marriage muhurtat dates (Shubh/Uttam — +15%/+25% gifting demand)
  • Marriage seasons (Nov-Dec, Feb-May — sustained uplift)
  • Year-end / financial year-end push (Dec, Mar)
  • Monsoon slowdown (Jun-Aug)
  • Pre-festive booking window (demand ramps up 2-3 weeks before festival)
"""
import calendar as _cal
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from models import HeroSalesData, ForecastData
from services.festival_calendar import (
    get_festival_multiplier,
    get_marriage_muhurtat_multiplier,
    MONTHLY_SEASONAL_FACTORS,
)

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Raw data loader ───────────────────────────────────────────────────────────

def _sales_df(db: Session) -> pd.DataFrame:
    records = db.query(HeroSalesData).all()
    if not records:
        return pd.DataFrame()
    rows = [{
        "invoice_date":  r.invoice_date,
        "sku_code":      r.sku_code,
        "model_name":    r.model_name,
        "variant":       r.variant or "",
        "colour":        r.colour or "",
        "quantity_sold": r.quantity_sold,
        "unit_price":    r.unit_price,
    } for r in records]
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["year"]  = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    return df


# ── Data-derived seasonal factors ─────────────────────────────────────────────

def _compute_data_seasonal_factors(df: pd.DataFrame) -> Dict[int, float]:
    """
    Compute actual seasonal index per month from uploaded sales data.
    Returns month → factor (1.0 = average month).
    For months with no data (< 2 years available), falls back to market prior.
    """
    if df.empty:
        return dict(MONTHLY_SEASONAL_FACTORS)

    monthly = df.groupby(["year", "month"])["quantity_sold"].sum().reset_index()
    avg_by_month = monthly.groupby("month")["quantity_sold"].mean()
    overall_avg  = float(avg_by_month.mean())

    if overall_avg == 0:
        return dict(MONTHLY_SEASONAL_FACTORS)

    factors: Dict[int, float] = {}
    for m in range(1, 13):
        if m in avg_by_month.index:
            # Use data-derived factor but blend with market prior for robustness
            data_factor   = float(avg_by_month[m]) / overall_avg
            market_factor = MONTHLY_SEASONAL_FACTORS.get(m, 1.0)
            # How many years of data for this month?
            n_years = int(monthly[monthly["month"] == m]["year"].nunique())
            weight  = min(n_years / 3, 1.0)   # full weight at 3+ years of data
            factors[m] = round(data_factor * weight + market_factor * (1 - weight), 3)
        else:
            factors[m] = MONTHLY_SEASONAL_FACTORS.get(m, 1.0)

    return factors


# ── SKU-level monthly rate table ──────────────────────────────────────────────

def _sku_monthly_rates(sku_df: pd.DataFrame) -> Dict[Tuple[int, int], float]:
    """
    Actual daily sales rate for a single SKU per (year, month).
    Returns {(year, month): units_per_day}.
    """
    rates: Dict[Tuple[int, int], float] = {}
    for (year, month), grp in sku_df.groupby(["year", "month"]):
        days = _cal.monthrange(int(year), int(month))[1]
        rates[(int(year), int(month))] = float(grp["quantity_sold"].sum()) / days
    return rates


# ── YoY trend ────────────────────────────────────────────────────────────────

def _yoy_trend_factor(sku_df: pd.DataFrame) -> float:
    """
    Estimate YoY growth factor from annual totals in the data.
    Clips to [0.80, 1.30] to avoid extreme swings.
    """
    annual = sku_df.groupby("year")["quantity_sold"].sum().reset_index()
    if len(annual) < 2:
        return 1.07   # default 7% growth when only 1 year of data
    years = annual["year"].values.astype(float)
    units = annual["quantity_sold"].values.astype(float)
    # Simple CAGR from first to last full year
    n = years[-1] - years[0]
    if n > 0 and units[0] > 0:
        cagr = (units[-1] / units[0]) ** (1.0 / n)
        return float(np.clip(cagr, 0.80, 1.30))
    return 1.07


# ── Combined demand multiplier for a date ────────────────────────────────────

def _demand_multiplier(target: date) -> Tuple[float, str]:
    """
    Returns the combined demand multiplier for a date, taking the highest
    signal among: festival boost, marriage muhurtat, or base 1.0.
    """
    fest_mult,  fest_name  = get_festival_multiplier(target)
    muhur_mult, muhur_name = get_marriage_muhurtat_multiplier(target)

    if muhur_mult > fest_mult:
        return muhur_mult, muhur_name or ""
    return fest_mult, fest_name or ""


# ── Per-SKU forecast ──────────────────────────────────────────────────────────

def forecast_sku(
    sku_df: pd.DataFrame,
    sku_meta: Dict,
    start_date: date,
    horizon_days: int = 60,
    data_seasonal_factors: Optional[Dict[int, float]] = None,
) -> List[Dict]:
    """
    Generate a day-by-day forecast for one SKU.

    Base rate strategy (data-first):
      1. LYSM anchor    — last-year same-month daily rate × trend
      2. Avg-month      — historical average for that month × trend
      3. Seasonal avg   — overall daily avg × data-derived seasonal factor
    Then multiply by festival / muhurtat demand boost.
    """
    if data_seasonal_factors is None:
        data_seasonal_factors = dict(MONTHLY_SEASONAL_FACTORS)

    monthly_rates = _sku_monthly_rates(sku_df)
    trend_factor  = _yoy_trend_factor(sku_df)

    # Overall daily average (for fallback)
    if not sku_df.empty:
        span_days  = max(1, (sku_df["invoice_date"].max() - sku_df["invoice_date"].min()).days + 1)
        overall_avg = float(sku_df["quantity_sold"].sum()) / span_days
    else:
        overall_avg = 0.5

    avg_price = float(sku_df["unit_price"].mean()) if not sku_df.empty else 0.0

    forecast = []
    for d in range(horizon_days):
        target   = start_date + timedelta(days=d)
        month    = target.month
        fc_year  = target.year
        ly_key   = (fc_year - 1, month)

        # ── Base rate selection (data-first) ─────────────────────────────────
        if ly_key in monthly_rates and monthly_rates[ly_key] > 0:
            # Best: last year same month actual daily rate × trend
            base   = monthly_rates[ly_key] * trend_factor
            method = "lysm"
        else:
            # Try: average of all data for this calendar month
            month_rates = [r for (y, m), r in monthly_rates.items() if m == month]
            if month_rates:
                base   = float(np.mean(month_rates)) * trend_factor
                method = "avg_month"
            else:
                # Fallback: overall avg × data-derived seasonal factor
                seasonal = data_seasonal_factors.get(month, 1.0)
                base     = overall_avg * seasonal * trend_factor
                method   = "avg_seasonal"

        # ── Festival / muhurtat boost ─────────────────────────────────────────
        demand_mult, event_name = _demand_multiplier(target)

        predicted = base * demand_mult

        # Confidence intervals widen with horizon
        ci_spread = 0.18 + (d / horizon_days) * 0.17   # 18 % → 35 %
        lower = max(0.0, predicted * (1.0 - ci_spread))
        upper = predicted * (1.0 + ci_spread)

        forecast.append({
            "forecast_date":     target,
            "sku_code":          sku_meta["sku_code"],
            "model_name":        sku_meta["model_name"],
            "variant":           sku_meta.get("variant") or "",
            "colour":            sku_meta.get("colour") or "",
            "predicted_quantity": round(predicted, 2),
            "confidence_lower":  round(lower, 2),
            "confidence_upper":  round(upper, 2),
            "festival_boost":    round(demand_mult, 3),
            "festival_name":     event_name,
            "forecast_method":   method,
        })
    return forecast


# ── Full-portfolio forecast ───────────────────────────────────────────────────

def run_full_forecast(db: Session, horizon_days: int = 60) -> List[Dict]:
    """Run forecast for ALL SKUs; returns flat list of daily forecast rows."""
    df = _sales_df(db)
    if df.empty:
        return []

    data_sf    = _compute_data_seasonal_factors(df)
    start_date = date.today()

    # Fill NaN in key columns to avoid SKU groupby dropping rows
    for col in ["sku_code", "model_name", "variant", "colour"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    skus = df[["sku_code", "model_name", "variant", "colour"]].drop_duplicates()

    all_forecasts = []
    for _, meta in skus.iterrows():
        sku_df = df[df["sku_code"] == meta["sku_code"]]
        fc     = forecast_sku(sku_df, meta.to_dict(), start_date, horizon_days, data_sf)
        all_forecasts.extend(fc)

    return all_forecasts


# ── Summary (per-SKU 30d/60d totals) ─────────────────────────────────────────

def get_forecast_summary(db: Session, horizon_days: int = 60) -> List[Dict]:
    """Return per-SKU 30-day and 60-day forecast totals with context."""
    forecasts = run_full_forecast(db, horizon_days)
    if not forecasts:
        return []

    fc_df = pd.DataFrame(forecasts)
    fc_df["forecast_date"] = pd.to_datetime(fc_df["forecast_date"])

    # Fill NaN so groupby doesn't silently drop rows
    for col in ["sku_code", "model_name", "variant", "colour"]:
        if col in fc_df.columns:
            fc_df[col] = fc_df[col].fillna("").astype(str)

    today  = pd.Timestamp(date.today())
    next30 = today + pd.Timedelta(days=30)

    result = []
    for (sku, model, variant, colour), grp in fc_df.groupby(
        ["sku_code", "model_name", "variant", "colour"]
    ):
        total_60 = float(grp["predicted_quantity"].sum())
        total_30 = float(grp[grp["forecast_date"] <= next30]["predicted_quantity"].sum())

        peak_idx = grp["predicted_quantity"].idxmax()
        peak_day = grp.loc[peak_idx, "forecast_date"].date() if pd.notna(peak_idx) else None

        max_boost = float(grp["festival_boost"].max())
        festival_impact = "High" if max_boost > 1.3 else "Medium" if max_boost > 1.1 else "Low"

        # Dominant forecast method (for transparency)
        method_counts = grp["forecast_method"].value_counts()
        dominant_method = method_counts.idxmax() if not method_counts.empty else "avg_seasonal"

        result.append({
            "sku_code":            sku,
            "model_name":          model,
            "variant":             variant,
            "colour":              colour,
            "total_forecast_30d":  round(total_30, 1),
            "total_forecast_60d":  round(total_60, 1),
            "peak_day":            peak_day,
            "festival_impact":     festival_impact,
            "max_festival_boost":  round(max_boost, 2),
            "forecast_method":     dominant_method,
        })

    return sorted(result, key=lambda x: x["total_forecast_60d"], reverse=True)


# ── Forecast accuracy from past data ─────────────────────────────────────────

def compute_forecast_accuracy(db: Session) -> Dict:
    """
    Back-test accuracy: for the most recent full month in the data,
    compute what the LYSM-anchor forecast would have predicted vs actual.
    Returns MAPE (mean absolute percentage error) and accuracy %.
    """
    df = _sales_df(db)
    if df.empty:
        return {"accuracy_pct": None, "mape_pct": None, "test_month": None}

    latest = df["invoice_date"].max()
    # Use 2nd most recent full month as test (most recent may be partial)
    if latest.month > 1:
        test_month = latest.month - 1
        test_year  = latest.year
    else:
        test_month = 12
        test_year  = latest.year - 1

    actual_df = df[(df["year"] == test_year) & (df["month"] == test_month)]
    if actual_df.empty:
        return {"accuracy_pct": None, "mape_pct": None, "test_month": None}

    data_sf = _compute_data_seasonal_factors(df)
    test_start = date(test_year, test_month, 1)
    test_days  = _cal.monthrange(test_year, test_month)[1]

    sku_errors = []
    for sku_code, sku_actual in actual_df.groupby("sku_code")["quantity_sold"].sum().items():
        if sku_actual == 0:
            continue
        sku_df = df[df["sku_code"] == sku_code]
        # Exclude the test month from training data for honest back-test
        train_df = sku_df[(sku_df["year"] < test_year) |
                          ((sku_df["year"] == test_year) & (sku_df["month"] < test_month))]
        if train_df.empty:
            continue

        meta = {"sku_code": sku_code,
                "model_name": str(sku_df["model_name"].iloc[0]),
                "variant": str(sku_df["variant"].iloc[0]) if "variant" in sku_df.columns else "",
                "colour":  str(sku_df["colour"].iloc[0])  if "colour"  in sku_df.columns else ""}
        fc = forecast_sku(train_df, meta, test_start, test_days, data_sf)
        predicted_total = sum(r["predicted_quantity"] for r in fc)
        if predicted_total > 0:
            ape = abs(sku_actual - predicted_total) / sku_actual * 100
            sku_errors.append(ape)

    if not sku_errors:
        return {"accuracy_pct": None, "mape_pct": None, "test_month": None}

    mape = round(float(np.mean(sku_errors)), 1)
    accuracy = round(max(0.0, 100.0 - mape), 1)

    return {
        "accuracy_pct": accuracy,
        "mape_pct":     mape,
        "test_month":   f"{MONTH_NAMES[test_month]} {test_year}",
        "sku_count":    len(sku_errors),
    }


# ── What-if simulation ────────────────────────────────────────────────────────

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
        shift_days = int(parameter)
        adjustment = 1.0 + (shift_days / 30) * 0.05
        adjusted_units = baseline_units * adjustment
        notes = (f"Diwali shifted {'+' if shift_days>0 else ''}{shift_days} days → "
                 f"demand pull {'forward' if shift_days<0 else 'later'}")

    elif scenario == "fuel_price":
        pct_change    = parameter   # e.g. 5 = +5%
        demand_effect = -pct_change * 0.3 / 100
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = f"Fuel price +{pct_change}% → estimated demand change: {round(demand_effect*100,1)}%"

    elif scenario == "competitor_launch":
        impact_score  = parameter   # 0–1
        demand_effect = -impact_score * 0.12
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = (f"Competitor launch (impact {impact_score}) → "
                 f"estimated demand drop: {round(-demand_effect*100,1)}%")

    elif scenario == "marriage_season":
        extra_days    = int(parameter)
        demand_effect = extra_days * 0.015
        adjusted_units = baseline_units * (1.0 + demand_effect)
        notes = f"{extra_days} extra marriage muhurtat days → uplift: {round(demand_effect*100,1)}%"

    else:
        adjusted_units = baseline_units
        notes = "Unknown scenario"

    delta = adjusted_units - baseline_units
    affected_skus = fc_df["sku_code"].unique().tolist()

    return {
        "scenario":       scenario,
        "parameter":      parameter,
        "baseline_units": round(float(baseline_units), 1),
        "adjusted_units": round(float(adjusted_units), 1),
        "delta_units":    round(float(delta), 1),
        "delta_pct":      round(float(delta / baseline_units * 100), 1) if baseline_units > 0 else 0.0,
        "affected_skus":  affected_skus[:20],
        "notes":          notes,
    }
