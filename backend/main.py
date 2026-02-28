"""
Two-Wheeler Sales Intelligence API
AI-powered analytics platform for Indian two-wheeler dealerships.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Two-Wheeler Sales Intelligence API…")
    init_db()
    logger.info("Database initialised.")

    # Seed sample data if the database is empty
    from scripts.generate_sample_data import seed_if_empty
    seed_if_empty()
    logger.info("Data seeding check complete.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Two-Wheeler Sales Intelligence API",
    description=(
        "AI-powered analytics & dispatch planning for Indian two-wheeler dealerships. "
        "Covers YoY/MoM analytics, festival intelligence, SKU forecasting, "
        "dispatch optimisation, and an AI copilot."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ───────────────────────────────────────────────────────────────────────
origins = settings.cors_origins.split(",") if "," in settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ────────────────────────────────────────────────────────────────────
from routes.sales import router as sales_router
from routes.forecast import router as forecast_router
from routes.dispatch import router as dispatch_router
from routes.festivals import router as festivals_router
from routes.alerts import router as alerts_router
from routes.copilot import router as copilot_router
from routes.market import router as market_router
from routes.stock import router as stock_router

app.include_router(sales_router,    prefix="/api/sales",     tags=["Sales Analytics"])
app.include_router(forecast_router, prefix="/api/forecast",  tags=["Forecasting"])
app.include_router(dispatch_router, prefix="/api/dispatch",  tags=["Dispatch Planning"])
app.include_router(festivals_router,prefix="/api/festivals", tags=["Festival Intelligence"])
app.include_router(alerts_router,   prefix="/api/alerts",    tags=["Smart Alerts"])
app.include_router(copilot_router,  prefix="/api/copilot",   tags=["AI Copilot"])
app.include_router(market_router,   prefix="/api/market",    tags=["Market Intelligence"])
app.include_router(stock_router,    prefix="/api/stock",     tags=["Stock Inventory"])


# ─── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Two-Wheeler Sales Intelligence API",
        "docs": "/docs",
        "health": "/api/health",
    }
