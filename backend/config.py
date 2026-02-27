import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration"""

    # Database - defaults to SQLite for easy local setup
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hero_sales.db")
    sqlalchemy_echo: bool = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

    # App
    app_name: str = os.getenv("APP_NAME", "Two-Wheeler Sales Intelligence")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # API
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # External APIs
    google_trends_api_key: str = os.getenv("GOOGLE_TRENDS_API_KEY", "")
    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Forecasting
    forecast_horizon_days: int = int(os.getenv("FORECAST_HORIZON_DAYS", "60"))
    confidence_interval: float = float(os.getenv("CONFIDENCE_INTERVAL", "0.8"))

    # Business
    default_lead_time_days: int = int(os.getenv("DEFAULT_LEAD_TIME_DAYS", "21"))
    buffer_stock_percent: float = float(os.getenv("BUFFER_STOCK_PERCENT", "0.15"))

    class Config:
        case_sensitive = False

settings = Settings()
