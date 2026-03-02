"""
Sales Target Engine
────────────────────────────────────────────────────────────────────────
• Auto-computes monthly targets as max(15% growth over last year same month,
  seasonal-adjusted growth) — whichever is higher.
• Supports model-wise target overrides (when company gives model targets).
• Overall target auto-adjusts when model targets are saved (replaces auto
  with sum of model targets + auto-fill for models without manual target).
• Pathway engine: shows daily run-rate needed, days remaining, weekly goals,
  festival/muhurtat boost windows, and risk assessment.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
import math

from models import HeroSalesData, SalesTarget
from services.festival_calendar import get_upcoming_festivals, MONTHLY_SEASONAL_FACTORS

MONTH_NAMES = {
    1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
    7:"July",8:"August",9:"September",10:"October",11:"November",12:"December",
}
MONTH_ABBR = {
    1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
    7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec",
}

MIN_GROWTH_PCT = 15.0   # minimum 15% over last year same month


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _sales_df(db: Session) -> pd.DataFrame:
    records = db.query(HeroSalesData).all()
    if not records:
        return pd.DataFrame()
    rows = [{"invoice_date": r.invoice_date, "model_name": r.model_name,
             "quantity_sold": r.quantity_sold, "unit_price": r.unit_price,
             "total_value": r.total_value} for r in records]
    df = pd.DataFrame(rows)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["year"]  = df["invoice_date"].dt.year
    df["month"] = df["invoice_date"].dt.month
    return df


def _last_year_same_month(df: pd.DataFrame, year: int, month: int, model: Optional[str]=None) -> int:
    """Units sold in the same month of the previous year (full month)."""
    sub = df[(df["year"]==year-1) & (df["month"]==month)]
    if model:
        sub = sub[sub["model_name"]==model]
    return int(sub["quantity_sold"].sum())


def _current_month_actuals(df: pd.DataFrame, year: int, month: int, model: Optional[str]=None) -> int:
    """Units sold so far this month."""
    sub = df[(df["year"]==year) & (df["month"]==month)]
    if model:
        sub = sub[sub["model_name"]==model]
    return int(sub["quantity_sold"].sum())


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return (date(year+1,1,1) - date(year,12,1)).days
    return (date(year, month+1, 1) - date(year, month, 1)).days


def _working_days_remaining(year: int, month: int, from_date: date) -> int:
    """Approximate working days left in the month (Mon-Sat, excludes Sun)."""
    last = date(year, month, _days_in_month(year, month))
    count = 0
    d = from_date
    while d <= last:
        if d.weekday() != 6:   # not Sunday
            count += 1
        d += timedelta(days=1)
    return count


def _seasonal_factor_for_month(month: int) -> float:
    return MONTHLY_SEASONAL_FACTORS.get(month, 1.0)


def _avg_monthly_units(df: pd.DataFrame, model: Optional[str]=None) -> float:
    sub = df if not model else df[df["model_name"]==model]
    if sub.empty:
        return 0.0
    monthly = sub.groupby(["year","month"])["quantity_sold"].sum().reset_index()
    return float(monthly["quantity_sold"].mean())


# ────────────────────────────────────────────────────────────────────────────
# Core: compute auto target for a month
# ────────────────────────────────────────────────────────────────────────────

def compute_auto_target(
    db: Session,
    year: int,
    month: int,
    model: Optional[str] = None,
    growth_pct: float = MIN_GROWTH_PCT,
) -> Dict[str, Any]:
    """
    Compute the recommended target for a given month and optional model.
    Target = max(
        last_year_same_month * (1 + growth_pct/100),
        avg_monthly * seasonal_factor
    )
    Always at least MIN_GROWTH_PCT above last year same month.
    """
    df = _sales_df(db)
    if df.empty:
        return {"target_units": 0, "basis_units": 0, "growth_pct": growth_pct,
                "method": "no_data", "model": model}

    ly_units   = _last_year_same_month(df, year, month, model)
    avg_units  = _avg_monthly_units(df, model)
    seas_factor= _seasonal_factor_for_month(month)

    # Option A: 15% (or given %) growth over last year
    target_a = math.ceil(ly_units * (1 + growth_pct / 100)) if ly_units > 0 else 0

    # Option B: seasonal average × 1.15
    target_b = math.ceil(avg_units * seas_factor * (1 + MIN_GROWTH_PCT/100)) if avg_units > 0 else 0

    # Pick higher of the two
    target = max(target_a, target_b)
    if target == 0:
        # fallback: if no history, use industry average monthly units
        target = max(10, math.ceil(avg_units * 1.15)) if avg_units > 0 else 10

    actual_growth = round((target - ly_units) / ly_units * 100, 1) if ly_units > 0 else growth_pct
    method = "yoy_growth" if target == target_a else "seasonal_adjusted"

    return {
        "year":          year,
        "month":         month,
        "month_name":    MONTH_NAMES[month],
        "model":         model,
        "target_units":  target,
        "basis_units":   ly_units,
        "avg_monthly":   round(avg_units, 1),
        "growth_pct":    actual_growth,
        "min_growth_pct":MIN_GROWTH_PCT,
        "method":        method,
        "seasonal_factor": seas_factor,
    }


# ────────────────────────────────────────────────────────────────────────────
# CRUD: save / load targets
# ────────────────────────────────────────────────────────────────────────────

def save_overall_target(
    db: Session,
    year: int,
    month: int,
    target_units: int,
    growth_pct: float,
    basis_units: int,
    is_manual: bool = False,
    notes: str = "",
) -> SalesTarget:
    existing = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month, SalesTarget.model_name==None)
    ).first()
    if existing:
        existing.target_units = target_units
        existing.growth_pct   = growth_pct
        existing.basis_units  = basis_units
        existing.is_manual    = is_manual
        existing.notes        = notes
        db.commit()
        db.refresh(existing)
        return existing
    new = SalesTarget(year=year, month=month, model_name=None,
                      target_units=target_units, growth_pct=growth_pct,
                      basis_units=basis_units, is_manual=is_manual, notes=notes)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def save_model_target(
    db: Session,
    year: int,
    month: int,
    model_name: str,
    target_units: int,
    notes: str = "",
) -> SalesTarget:
    df = _sales_df(db)
    ly = _last_year_same_month(df, year, month, model_name)
    gp = round((target_units - ly) / ly * 100, 1) if ly > 0 else 0.0

    existing = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month,
             SalesTarget.model_name==model_name)
    ).first()
    if existing:
        existing.target_units = target_units
        existing.growth_pct   = gp
        existing.basis_units  = ly
        existing.is_manual    = True
        existing.notes        = notes
        db.commit()
        db.refresh(existing)
    else:
        existing = SalesTarget(year=year, month=month, model_name=model_name,
                               target_units=target_units, growth_pct=gp,
                               basis_units=ly, is_manual=True, notes=notes)
        db.add(existing)
        db.commit()
        db.refresh(existing)

    # Recompute overall target = sum of all model targets + remaining auto
    _recompute_overall_from_models(db, year, month)
    return existing


def _recompute_overall_from_models(db: Session, year: int, month: int):
    """Update overall target as sum of model targets when model targets are set."""
    model_targets = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month,
             SalesTarget.model_name != None)
    ).all()
    if not model_targets:
        return
    total = sum(t.target_units for t in model_targets)
    # Update overall
    overall = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month, SalesTarget.model_name==None)
    ).first()
    if overall:
        overall.target_units = total
        overall.notes = f"Auto-updated from {len(model_targets)} model targets"
        db.commit()


def get_targets_for_month(db: Session, year: int, month: int) -> Dict[str, Any]:
    """Return overall + model-wise targets for a month."""
    all_targets = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month)
    ).all()

    overall = next((t for t in all_targets if t.model_name is None), None)
    models  = [t for t in all_targets if t.model_name is not None]

    df = _sales_df(db)

    # If no overall target saved, auto-compute
    if not overall:
        auto = compute_auto_target(db, year, month)
        overall_data = auto
    else:
        overall_data = {
            "year": overall.year, "month": overall.month,
            "month_name": MONTH_NAMES[overall.month],
            "target_units": overall.target_units,
            "basis_units": overall.basis_units,
            "growth_pct": overall.growth_pct,
            "is_manual": overall.is_manual,
            "notes": overall.notes,
        }

    model_data = []
    for t in models:
        actuals = _current_month_actuals(df, year, month, t.model_name)
        model_data.append({
            "model_name":   t.model_name,
            "target_units": t.target_units,
            "basis_units":  t.basis_units,
            "growth_pct":   t.growth_pct,
            "is_manual":    t.is_manual,
            "actuals_so_far": actuals,
            "achievement_pct": round(actuals/t.target_units*100,1) if t.target_units>0 else 0,
            "remaining":    max(0, t.target_units - actuals),
            "notes":        t.notes,
        })

    return {
        "year":  year,
        "month": month,
        "month_name": MONTH_NAMES[month],
        "overall": overall_data,
        "model_targets": sorted(model_data, key=lambda x: x["target_units"], reverse=True),
        "has_model_targets": len(models) > 0,
    }


def delete_model_target(db: Session, year: int, month: int, model_name: str) -> bool:
    rec = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month,
             SalesTarget.model_name==model_name)
    ).first()
    if rec:
        db.delete(rec)
        db.commit()
        _recompute_overall_from_models(db, year, month)
        return True
    return False


# ────────────────────────────────────────────────────────────────────────────
# Pathway Engine
# ────────────────────────────────────────────────────────────────────────────

def get_target_pathway(db: Session, year: int, month: int) -> Dict[str, Any]:
    """
    Compute the achievement pathway for the current month's target.
    Returns:
      • actuals so far, target, gap
      • daily run-rate needed
      • working days remaining
      • week-by-week goals
      • upcoming festival/muhurtat boosts within month
      • risk level (on-track / at-risk / critical)
      • model-wise pathway (if model targets set)
    """
    today = date.today()
    df    = _sales_df(db)

    # Determine reference date for this month
    if today.year == year and today.month == month:
        ref_date = today
    else:
        # Historical month: use last day of month
        ref_date = date(year, month, _days_in_month(year, month))

    # Get target
    target_rec = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month, SalesTarget.model_name==None)
    ).first()
    if target_rec:
        target_units = target_rec.target_units
        basis_units  = target_rec.basis_units or 0
        growth_pct   = target_rec.growth_pct or MIN_GROWTH_PCT
    else:
        auto = compute_auto_target(db, year, month)
        target_units = auto["target_units"]
        basis_units  = auto["basis_units"]
        growth_pct   = auto["growth_pct"]

    # Actuals so far this month
    actuals = _current_month_actuals(df, year, month)
    gap     = max(0, target_units - actuals)
    achieved_pct = round(actuals / target_units * 100, 1) if target_units > 0 else 0

    # Days / working days
    total_days     = _days_in_month(year, month)
    days_elapsed   = (ref_date - date(year, month, 1)).days + 1
    days_remaining = total_days - days_elapsed
    wdays_remaining= _working_days_remaining(year, month, ref_date + timedelta(days=1))

    # Run rate
    daily_needed   = math.ceil(gap / max(1, days_remaining))
    wday_needed    = math.ceil(gap / max(1, wdays_remaining))
    current_daily  = round(actuals / max(1, days_elapsed), 1)
    required_daily = round(target_units / max(1, total_days), 1)

    # Risk assessment
    if achieved_pct >= 100:
        risk = "achieved"
    elif days_remaining <= 0:
        risk = "month_end"
    else:
        projected = actuals + (current_daily * days_remaining)
        proj_pct  = projected / target_units * 100 if target_units > 0 else 0
        if proj_pct >= 95:
            risk = "on_track"
        elif proj_pct >= 80:
            risk = "at_risk"
        else:
            risk = "critical"

    # Week-by-week plan
    weeks = []
    week_start = date(year, month, 1)
    month_end  = date(year, month, _days_in_month(year, month))
    units_per_day = daily_needed if gap > 0 else required_daily
    wk_num = 1
    while week_start <= month_end:
        week_end = min(week_start + timedelta(days=6), month_end)
        days_in_wk = (week_end - week_start).days + 1
        wk_target  = math.ceil(units_per_day * days_in_wk)
        weeks.append({
            "week": wk_num,
            "start": str(week_start),
            "end":   str(week_end),
            "days":  days_in_wk,
            "target_units": wk_target,
        })
        week_start = week_end + timedelta(days=1)
        wk_num += 1

    # Upcoming festival / muhurtat boosts within this month
    month_start_d = date(year, month, 1)
    boost_events = get_upcoming_festivals(from_date=month_start_d, days_ahead=total_days)
    festival_days = [{
        "name": f["name"],
        "date": str(f["date"]),
        "impact_pct": f["impact_pct"],
        "days_away": f["days_away"],
        "action": f"Stock up 3-4 weeks before {f['name']} — expect +{f['impact_pct']}% demand"
    } for f in boost_events]

    # Estimated festival uplift on remaining gap
    if festival_days:
        max_boost = max(f["impact_pct"] for f in festival_days)
        festival_uplift = math.ceil(gap * max_boost / 100) if gap > 0 else 0
    else:
        festival_uplift = 0

    # Model-wise pathways (if model targets set)
    model_targets = db.query(SalesTarget).filter(
        and_(SalesTarget.year==year, SalesTarget.month==month, SalesTarget.model_name!=None)
    ).all()

    model_pathways = []
    for mt in model_targets:
        m_actual = _current_month_actuals(df, year, month, mt.model_name)
        m_gap    = max(0, mt.target_units - m_actual)
        m_daily  = math.ceil(m_gap / max(1, days_remaining)) if m_gap > 0 else 0
        m_pct    = round(m_actual / mt.target_units * 100, 1) if mt.target_units > 0 else 0
        # risk per model
        if m_pct >= 100:
            m_risk = "achieved"
        elif days_remaining > 0:
            proj = m_actual + (current_daily * days_remaining * (mt.target_units / max(1, target_units)))
            m_risk = "on_track" if proj/mt.target_units >= 0.95 else \
                     "at_risk"  if proj/mt.target_units >= 0.80 else "critical"
        else:
            m_risk = "month_end"
        model_pathways.append({
            "model_name":     mt.model_name,
            "target_units":   mt.target_units,
            "actuals":        m_actual,
            "gap":            m_gap,
            "achieved_pct":   m_pct,
            "daily_needed":   m_daily,
            "risk":           m_risk,
        })

    # Key actions
    actions = []
    if risk == "critical":
        actions.append("URGENT: Daily sales rate is far below target — push promotions, follow up on pending bookings.")
    if risk == "at_risk":
        actions.append("Increase showroom walk-ins. Run weekend campaigns and test-ride drives.")
    if festival_uplift > 0:
        actions.append(f"Festival season boost expected to contribute ~{festival_uplift} extra units.")
    if wdays_remaining > 0:
        actions.append(f"Need {daily_needed} units/day ({wday_needed} units/working day) for remaining {days_remaining} days.")
    actions.append(f"Top model today: focus sales team efforts on highest-velocity SKUs.")

    return {
        "year":           year,
        "month":          month,
        "month_name":     MONTH_NAMES[month],
        "ref_date":       str(ref_date),
        "target_units":   target_units,
        "actuals_so_far": actuals,
        "gap":            gap,
        "achieved_pct":   achieved_pct,
        "basis_units":    basis_units,
        "growth_pct":     growth_pct,
        "days_total":     total_days,
        "days_elapsed":   days_elapsed,
        "days_remaining": days_remaining,
        "working_days_remaining": wdays_remaining,
        "current_daily_rate":  current_daily,
        "required_daily_rate": required_daily,
        "daily_needed":        daily_needed,
        "wday_needed":         wday_needed,
        "risk":                risk,
        "festival_events":     festival_days,
        "festival_uplift_est": festival_uplift,
        "weekly_plan":         weeks,
        "model_pathways":      sorted(model_pathways, key=lambda x: x["target_units"], reverse=True),
        "key_actions":         actions,
    }


def get_full_year_target_plan(db: Session, year: int) -> List[Dict]:
    """
    All 12 months' targets for a year with YoY context.
    Used for annual planning view.
    """
    df = _sales_df(db)
    result = []
    for month in range(1, 13):
        ly    = _last_year_same_month(df, year, month)
        auto  = compute_auto_target(db, year, month)
        saved = db.query(SalesTarget).filter(
            and_(SalesTarget.year==year, SalesTarget.month==month, SalesTarget.model_name==None)
        ).first()
        target = saved.target_units if saved else auto["target_units"]
        actuals= _current_month_actuals(df, year, month)
        result.append({
            "month":       month,
            "month_name":  MONTH_ABBR[month],
            "last_year":   ly,
            "target":      target,
            "actuals":     actuals,
            "is_set":      saved is not None,
            "is_future":   date(year, month, 1) > date.today(),
            "achieved_pct":round(actuals/target*100,1) if target>0 else 0,
            "seasonal_factor": _seasonal_factor_for_month(month),
        })
    return result
