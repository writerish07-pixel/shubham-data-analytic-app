"""
AI Copilot Service
Rule-based + optional LLM-backed conversational analytics assistant.
"""
import re
from datetime import date
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from services.sales_analytics import get_sku_performance, get_colour_analysis, get_yoy_analysis
from services.festival_calendar import (
    get_festival_impact_history, get_upcoming_festivals,
    get_marriage_season_info, FESTIVAL_CALENDAR
)
from services.forecasting import get_forecast_summary
from services.dispatch_planner import generate_dispatch_recommendations

# ─── Suggested starter questions ─────────────────────────────────────────────────
SUGGESTED_QUESTIONS = [
    "How much should I dispatch next month?",
    "What was the Diwali spike over the last 3 years?",
    "Which colour sells best during Navratri?",
    "Which are my slowest moving SKUs?",
    "What is the marriage season forecast?",
    "Show me top performing models this year",
    "Which SKUs have overstock risk?",
    "What is the impact of fuel price increase?",
]


def _extract_intent(message: str) -> str:
    msg = message.lower()
    if any(k in msg for k in ["dispatch", "order", "recommend", "how much"]):
        return "dispatch"
    if any(k in msg for k in ["diwali", "navratri", "onam", "pongal", "festival", "spike", "festiv"]):
        return "festival"
    if any(k in msg for k in ["colour", "color"]):
        return "colour"
    if any(k in msg for k in ["marriage", "wedding", "muhurat", "shaadi"]):
        return "marriage"
    if any(k in msg for k in ["slow", "dead stock", "dead-stock", "slow-mov"]):
        return "slow_movers"
    if any(k in msg for k in ["top", "best", "rank", "performance", "highest"]):
        return "top_performers"
    if any(k in msg for k in ["risk", "overstock", "under"]):
        return "risk"
    if any(k in msg for k in ["forecast", "predict", "next month", "future"]):
        return "forecast"
    if any(k in msg for k in ["yoy", "year", "growth", "trend"]):
        return "yoy"
    if any(k in msg for k in ["fuel", "petrol", "diesel"]):
        return "fuel"
    return "general"


def _extract_festival_name(message: str) -> Optional[str]:
    festivals = ["diwali", "dhanteras", "navratri", "dussehra", "onam", "pongal",
                 "akshaya tritiya", "eid", "holi", "holi", "bhai dooj"]
    for f in festivals:
        if f in message.lower():
            return f.title()
    return None


def _dispatch_response(db: Session, message: str) -> Dict:
    recs = generate_dispatch_recommendations(db)
    total = sum(r["total_dispatch"] for r in recs)
    top5 = recs[:5]

    lines = [f"**Dispatch Recommendation for Next 30 Days**\n"]
    lines.append(f"Total units to dispatch across all SKUs: **{total:,}**\n")
    lines.append("\nTop priority SKUs:\n")
    for r in top5:
        emoji = "🔴" if r["risk_type"] == "understock" else "🟡" if r["risk_type"] == "overstock" else "🟢"
        lines.append(f"{emoji} **{r['model_name']} {r['colour']}** ({r['sku_code']}): "
                     f"{r['total_dispatch']} units | Risk: {r['risk_type']}")
    lines.append("\n\n*Use the Dispatch Planner tab for full SKU-wise breakdown.*")

    return {
        "answer": "\n".join(lines),
        "data": {"recommendations": top5, "total_dispatch": total},
        "chart_type": "dispatch_table",
        "suggested_followups": [
            "Which SKUs are at understock risk?",
            "Show me working capital impact",
            "What is the festival adjustment for next month?",
        ],
    }


def _festival_response(db: Session, message: str) -> Dict:
    festival_name = _extract_festival_name(message)

    # Historical impact
    if festival_name:
        history = get_festival_impact_history(festival_name)
        if history:
            lines = [f"**{festival_name} – Historical Sales Impact**\n"]
            for h in history[-4:]:
                lines.append(f"• {h['year']}: Festival date {h['date'].strftime('%d %b')} | "
                             f"Expected uplift: **{h['impact_pct']}%**")
            lines.append("\n*Demand typically ramps up 14–21 days before the festival.*")
            return {
                "answer": "\n".join(lines),
                "data": {"festival": festival_name, "history": [
                    {"year": h["year"], "date": str(h["date"]), "impact_pct": h["impact_pct"]}
                    for h in history[-4:]
                ]},
                "chart_type": "festival_bar",
                "suggested_followups": [
                    f"Which colour sells best during {festival_name}?",
                    f"How much extra stock for {festival_name}?",
                    "Show upcoming festivals",
                ],
            }

    # Upcoming festivals
    upcoming = get_upcoming_festivals(days_ahead=90)
    lines = ["**Upcoming Festivals & Expected Impact**\n"]
    for f in upcoming[:6]:
        lines.append(f"• **{f['name']}** – {f['date'].strftime('%d %b %Y')} "
                     f"({f['days_away']} days away) | Impact: +{f['impact_pct']}%")
    return {
        "answer": "\n".join(lines),
        "data": {"upcoming": [
            {"name": f["name"], "date": str(f["date"]), "days_away": f["days_away"],
             "impact_pct": f["impact_pct"]} for f in upcoming[:6]
        ]},
        "chart_type": "timeline",
        "suggested_followups": ["Show Diwali spike history", "Marriage season forecast"],
    }


def _colour_response(db: Session, message: str) -> Dict:
    festival_name = _extract_festival_name(message)
    colours = get_colour_analysis(db)

    lines = ["**Colour-wise Sales Analysis**\n"]
    for c in colours[:8]:
        lines.append(f"• {c['colour']}: {c['total_units']:,} units "
                     f"({c['share_pct']}%) | YoY: {'+' if (c.get('yoy_growth') or 0) > 0 else ''}"
                     f"{c.get('yoy_growth', 'N/A')}%")

    if festival_name:
        lines.insert(1, f"\n*During {festival_name}, bright colours (Red, White, Blue) typically see higher demand.*\n")

    return {
        "answer": "\n".join(lines),
        "data": {"colours": colours[:8]},
        "chart_type": "colour_pie",
        "suggested_followups": ["Which colour is growing fastest?", "Top SKU by colour"],
    }


def _marriage_response(db: Session, message: str) -> Dict:
    info = get_marriage_season_info()
    lines = ["**Marriage Season Intelligence**\n"]
    if info:
        lines.append(f"Next marriage season: **{info['season']}** (in ~{info['days_away']} days)\n")
        lines.append(f"Expected sales uplift: **+{info['uplift_pct']}%**\n")
        lines.append(f"Recommended colours to stock: {', '.join(info['recommended_colours'])}")
        lines.append(f"Vehicle type demand: {', '.join(info['recommended_types'])}")
        lines.append("\n*Scooters see higher demand during marriage season (gifting pattern).*")
    else:
        lines.append("No upcoming marriage season window detected in the next 30 days.")

    return {
        "answer": "\n".join(lines),
        "data": info,
        "chart_type": "marriage_timeline",
        "suggested_followups": [
            "Which colours sell best in marriage season?",
            "How much extra stock should I keep for marriage season?",
        ],
    }


def _slow_movers_response(db: Session, message: str) -> Dict:
    sku_perf = get_sku_performance(db)
    slow = [s for s in sku_perf if s["is_slow_moving"]]

    lines = ["**Slow-Moving SKU Alert**\n"]
    if slow:
        lines.append(f"Found **{len(slow)} slow-moving SKUs**:\n")
        for s in slow[:8]:
            lines.append(f"• {s['model_name']} {s['colour']} ({s['sku_code']}): "
                         f"{s['avg_monthly_units']:.1f} units/month | Dead stock risk: {int(s['dead_stock_risk']*100)}%")
        lines.append("\n*Recommendation: Reduce dispatch for these SKUs and run promotional campaigns.*")
    else:
        lines.append("No slow-moving SKUs detected in current data.")

    return {
        "answer": "\n".join(lines),
        "data": {"slow_movers": slow[:8]},
        "chart_type": "risk_table",
        "suggested_followups": ["Which SKUs have overstock risk?", "Show dispatch recommendations"],
    }


def _top_performers_response(db: Session, message: str) -> Dict:
    sku_perf = get_sku_performance(db)[:10]
    lines = ["**Top Performing SKUs**\n"]
    for i, s in enumerate(sku_perf[:8], 1):
        yoy_str = f"+{s['yoy_growth_percent']}%" if s.get("yoy_growth_percent") and s["yoy_growth_percent"] > 0 else ""
        lines.append(f"{i}. **{s['model_name']} {s['colour']}** ({s['sku_code']}): "
                     f"{s['total_units_sold']:,} units {yoy_str}")
    return {
        "answer": "\n".join(lines),
        "data": {"top_performers": sku_perf[:8]},
        "chart_type": "ranking_bar",
        "suggested_followups": ["Show YoY growth trend", "Which models should I dispatch more of?"],
    }


def _forecast_response(db: Session, message: str) -> Dict:
    summaries = get_forecast_summary(db, horizon_days=60)[:10]
    lines = ["**60-Day Forecast Summary**\n"]
    for s in summaries[:8]:
        lines.append(f"• **{s['model_name']} {s['colour']}**: "
                     f"{s['total_forecast_30d']:.0f} units (30d) | "
                     f"{s['total_forecast_60d']:.0f} units (60d) | "
                     f"Festival impact: {s['festival_impact']}")
    return {
        "answer": "\n".join(lines),
        "data": {"forecast": summaries[:8]},
        "chart_type": "forecast_line",
        "suggested_followups": ["Show dispatch plan based on forecast", "What-if Diwali shifts 10 days?"],
    }


def _general_response(message: str) -> Dict:
    return {
        "answer": (
            "I'm your **Two-Wheeler Sales Intelligence Copilot**. I can help with:\n\n"
            "• 📦 Dispatch planning & recommendations\n"
            "• 🎆 Festival impact & Diwali/Navratri analysis\n"
            "• 🎨 Colour & variant demand analysis\n"
            "• 💒 Marriage season stock planning\n"
            "• 📈 YoY/MoM growth trends\n"
            "• ⚠️ Slow-moving stock alerts\n\n"
            "Try asking: *'How much should I dispatch next month?'*"
        ),
        "data": None,
        "chart_type": None,
        "suggested_followups": SUGGESTED_QUESTIONS[:4],
    }


def process_copilot_query(db: Session, message: str, history: List[Dict] = None) -> Dict:
    """Main copilot entry point – routes query to the correct handler."""
    intent = _extract_intent(message)

    handlers = {
        "dispatch":      _dispatch_response,
        "festival":      _festival_response,
        "colour":        _colour_response,
        "marriage":      _marriage_response,
        "slow_movers":   _slow_movers_response,
        "top_performers": _top_performers_response,
        "forecast":      _forecast_response,
        "risk":          _slow_movers_response,
        "yoy":           lambda db, msg: {
            "answer": "Fetching YoY analysis...\n\nUse the **Sales Analytics** tab for the interactive YoY chart.",
            "data": get_yoy_analysis(db)[-12:],
            "chart_type": "yoy_line",
            "suggested_followups": ["Which month has highest growth?", "Show top performers"],
        },
        "fuel": lambda db, msg: {
            "answer": (
                "**Fuel Price Impact Simulation**\n\n"
                "A 5% increase in fuel price typically reduces two-wheeler demand by ~1.5%.\n"
                "Premium bikes (>₹1L) see less impact than budget commuters.\n\n"
                "Use the **What-If Simulator** in the Forecast tab for detailed analysis."
            ),
            "data": None,
            "chart_type": None,
            "suggested_followups": ["Run what-if for fuel price +5%", "Show demand forecast"],
        },
    }

    handler = handlers.get(intent, lambda db, msg: _general_response(msg))
    return handler(db, message)
