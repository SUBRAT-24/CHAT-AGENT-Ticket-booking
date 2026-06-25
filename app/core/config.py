"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "museum_ticketing"

    # Google Gemini AI
    GOOGLE_API_KEY: str = ""

    # Stripe Payment
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # JWT Auth
    SECRET_KEY: str = "default-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # App Settings
    APP_NAME: str = "Museum Ticketing Bot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8000"]'

    # Museum Settings
    MUSEUM_NAME: str = "National Heritage Museum"
    MUSEUM_CURRENCY: str = "INR"
    MUSEUM_TIMEZONE: str = "Asia/Kolkata"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
