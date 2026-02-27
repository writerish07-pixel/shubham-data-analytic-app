from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ─── Sales Schemas ──────────────────────────────────────────────────────────────

class SaleRecord(BaseModel):
    id: int
    invoice_date: date
    sku_code: str
    model_name: str
    variant: str
    colour: str
    quantity_sold: int
    unit_price: float
    total_value: float
    location: Optional[str] = None
    region: Optional[str] = None

    class Config:
        from_attributes = True


class YoYDataPoint(BaseModel):
    month: str
    year: int
    units: int
    revenue: float
    growth_pct: Optional[float] = None


class MoMDataPoint(BaseModel):
    month: str
    year: int
    units: int
    revenue: float
    mom_growth_pct: Optional[float] = None


class SKUPerformanceOut(BaseModel):
    sku_code: str
    model_name: str
    variant: str
    colour: str
    total_units_sold: int
    total_revenue: float
    yoy_growth_percent: Optional[float] = None
    mom_growth_percent: Optional[float] = None
    last_month_units: int
    current_month_units: int
    avg_monthly_units: float
    is_slow_moving: bool
    dead_stock_risk: float

    class Config:
        from_attributes = True


class ColourAnalysis(BaseModel):
    colour: str
    total_units: int
    revenue: float
    share_pct: float
    yoy_growth: Optional[float] = None


class SeasonalPattern(BaseModel):
    month: int
    month_name: str
    avg_units: float
    seasonal_factor: float
    festival_months: bool


# ─── Forecast Schemas ────────────────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    forecast_date: date
    sku_code: str
    model_name: str
    predicted_quantity: float
    confidence_lower: float
    confidence_upper: float
    festival_boost: float
    forecast_method: str


class ForecastSummary(BaseModel):
    sku_code: str
    model_name: str
    variant: str
    colour: str
    total_forecast_30d: float
    total_forecast_60d: float
    peak_day: Optional[date] = None
    festival_impact: str


class WhatIfRequest(BaseModel):
    scenario: str = Field(..., description="diwali_shift | fuel_price | competitor_launch")
    parameter: float = Field(..., description="Shift in days / % change / impact score")
    sku_codes: Optional[List[str]] = None


class WhatIfResult(BaseModel):
    scenario: str
    parameter: float
    baseline_units: float
    adjusted_units: float
    delta_units: float
    delta_pct: float
    affected_skus: List[str]
    notes: str


# ─── Dispatch Schemas ────────────────────────────────────────────────────────────

class DispatchRecommendationOut(BaseModel):
    sku_code: str
    model_name: str
    variant: str
    colour: str
    recommended_quantity: int
    buffer_stock: int
    total_dispatch: int
    risk_score: float
    risk_type: str
    working_capital_impact: float
    festival_factor: float
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class WorkingCapitalSummary(BaseModel):
    total_dispatch_value: float
    total_buffer_value: float
    dead_stock_exposure: float
    capital_rotation_days: float
    high_risk_skus: List[str]


class DispatchSimulationRequest(BaseModel):
    scenario: str
    parameters: Dict[str, Any]


# ─── Festival Schemas ────────────────────────────────────────────────────────────

class FestivalEvent(BaseModel):
    name: str
    date: date
    festival_type: str
    days_away: int
    expected_impact_pct: float
    affected_models: List[str]
    region: Optional[str] = None


class FestivalImpactAnalysis(BaseModel):
    festival_name: str
    year: int
    pre_festival_spike_pct: float
    peak_day_units: int
    total_festival_window_units: int
    top_sku: str
    top_colour: str


class MarriageSeasonInfo(BaseModel):
    season: str
    start_date: date
    end_date: date
    days_away: int
    expected_uplift_pct: float
    recommended_colours: List[str]
    recommended_models: List[str]


# ─── Alert Schemas ────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    alert_type: str
    priority: str
    title: str
    message: str
    sku_code: Optional[str] = None
    related_festival: Optional[str] = None
    action_required: bool
    is_dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── AI Copilot Schemas ──────────────────────────────────────────────────────────

class CopilotMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class CopilotRequest(BaseModel):
    message: str
    history: Optional[List[CopilotMessage]] = []


class CopilotResponse(BaseModel):
    answer: str
    data: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    suggested_followups: List[str] = []


# ─── Market Intelligence Schemas ─────────────────────────────────────────────────

class MarketTrend(BaseModel):
    category: str
    title: str
    summary: str
    impact_score: float
    data_date: date
    source: str


class DashboardSummary(BaseModel):
    total_units_ytd: int
    total_revenue_ytd: float
    yoy_growth_pct: float
    active_alerts: int
    top_sku: str
    top_model: str
    top_colour: str
    forecast_accuracy_pct: float
    monthly_trend: List[Dict[str, Any]]
    sku_rankings: List[Dict[str, Any]]
