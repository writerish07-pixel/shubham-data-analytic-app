import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/hero_sales_db")
    sqlalchemy_echo: bool = os.getenv("SQLALCHEMY_ECHO", "True").lower() == "true"
    
    # App
    app_name: str = os.getenv("APP_NAME", "Hero MotoCorp Sales Intelligence")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    
    # API
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    
    # External APIs
    google_trends_api_key: str = os.getenv("GOOGLE_TRENDS_API_KEY", "")
    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Forecasting
    forecast_horizon_days: int = int(os.getenv("FORECAST_HORIZON_DAYS", "60"))
    prophet_seasonality_mode: str = os.getenv("PROPHET_SEASONALITY_MODE", "additive")
    xgboost_max_depth: int = int(os.getenv("XGBOOST_MAX_DEPTH", "6"))
    
    class Config:
        case_sensitive = False

settings = Settings()