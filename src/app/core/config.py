"""Core configuration for the crypto data API."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Simple Crypto Data API"
    api_prefix: str = "/api/v1"
    default_exchange: str = "binance"
    default_market_type: str = "spot"
    enable_rate_limit: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
