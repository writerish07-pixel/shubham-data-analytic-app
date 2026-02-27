from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from database import get_db

router = APIRouter()

# Curated market intelligence (in production: pulled from News API / Google Trends)
MARKET_DATA = [
    {
        "category": "ev_trends",
        "title": "EV Two-Wheeler Sales Grow 35% YoY in India",
        "summary": (
            "Electric two-wheelers now account for 4.7% of total two-wheeler sales. "
            "Ola Electric, Ather, and TVS iQube lead the segment. "
            "Government FAME-II subsidies and rising petrol prices are key growth drivers."
        ),
        "impact_score": -0.15,
        "source": "SIAM Industry Report",
        "data_date": "2025-01-15",
        "tags": ["EV", "market_share", "competitor"],
    },
    {
        "category": "competitor",
        "title": "Honda Launches Activa EV – Scooter Segment Competition Intensifies",
        "summary": (
            "Honda's Activa EV launch at ₹1.17L targets the premium scooter segment. "
            "Destini 125 and Maestro Edge 125 may see 5–8% demand impact in metro markets."
        ),
        "impact_score": -0.2,
        "source": "AutoCar India",
        "data_date": "2025-02-01",
        "tags": ["competitor", "scooter", "Honda"],
    },
    {
        "category": "fuel",
        "title": "Petrol Prices Stable – No Revision Expected Before Elections",
        "summary": (
            "Petrol prices stable at ₹95–103/litre across major cities. "
            "Stable fuel prices are a positive for ICE two-wheeler demand. "
            "Analysts expect no hike until Q3 2025."
        ),
        "impact_score": 0.05,
        "source": "Economic Times",
        "data_date": "2025-02-10",
        "tags": ["fuel", "petrol", "demand"],
    },
    {
        "category": "policy",
        "title": "FAME-III Scheme Expected to Boost EV Adoption Further",
        "summary": (
            "Government to extend FAME subsidies under FAME-III framework. "
            "Expected to lower EV price by ₹10,000–15,000. "
            "May accelerate ICE-to-EV shift in the 125cc+ segment."
        ),
        "impact_score": -0.10,
        "source": "Ministry of Heavy Industries",
        "data_date": "2025-01-28",
        "tags": ["policy", "EV", "FAME"],
    },
    {
        "category": "trends",
        "title": "Splendor Plus Search Trends Up 18% – Commuter Segment Buoyant",
        "summary": (
            "Google Trends shows 18% YoY increase in searches for 'Splendor Plus price'. "
            "Rural market demand recovery driving commuter bike interest. "
            "Monsoon recovery expected to further boost H2 rural sales."
        ),
        "impact_score": 0.18,
        "source": "Google Trends",
        "data_date": "2025-02-15",
        "tags": ["trends", "Splendor", "rural"],
    },
    {
        "category": "market",
        "title": "Two-Wheeler Industry Grows 8% YoY in Jan 2025",
        "summary": (
            "Total industry volume at 1.7 million units in January 2025. "
            "Motorcycles up 9%, scooters up 6%. Premium segment (>150cc) up 14%. "
            "Rural market recovery remains key growth driver."
        ),
        "impact_score": 0.08,
        "source": "SIAM",
        "data_date": "2025-02-05",
        "tags": ["industry", "growth", "SIAM"],
    },
    {
        "category": "trends",
        "title": "Xtreme 160R Demand Rising Among Youth – Urban Markets",
        "summary": (
            "Sport bike segment sees 22% growth. Xtreme 160R trending on social media. "
            "Younger buyers (18–28) driving premium motorcycle demand. "
            "Recommendation: Increase Xtreme 160R dispatch for Tier-1 cities."
        ),
        "impact_score": 0.22,
        "source": "Social Media Analytics",
        "data_date": "2025-02-12",
        "tags": ["trends", "Xtreme", "youth"],
    },
]


@router.get("/trends")
def market_trends():
    return [m for m in MARKET_DATA if m["category"] in ("trends", "market")]


@router.get("/competitor-news")
def competitor_news():
    return [m for m in MARKET_DATA if m["category"] == "competitor"]


@router.get("/ev-trends")
def ev_trends():
    return [m for m in MARKET_DATA if m["category"] == "ev_trends"]


@router.get("/all")
def all_market_data():
    return MARKET_DATA


@router.get("/fuel")
def fuel_prices():
    return [m for m in MARKET_DATA if m["category"] == "fuel"]


@router.get("/policy")
def policy_updates():
    return [m for m in MARKET_DATA if m["category"] == "policy"]
