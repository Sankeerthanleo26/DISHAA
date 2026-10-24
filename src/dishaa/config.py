"""Application settings, read from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DISHAA_", extra="ignore")

    database_url: str = "postgresql://dishaa:dishaa_dev_password@localhost:5432/dishaa"

    # Scraper politeness. The User-Agent tells site owners who we are and where to reach us.
    user_agent: str = "Dishaa/0.1 (student project; +https://github.com/Sankeerthanleo26/DISHAA)"
    request_delay_seconds: float = 2.0
    request_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
