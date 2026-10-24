"""Application settings, read from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DISHAA_", extra="ignore")

    database_url: str = "postgresql://dishaa:dishaa_dev_password@localhost:5432/dishaa"


@lru_cache
def get_settings() -> Settings:
    return Settings()
