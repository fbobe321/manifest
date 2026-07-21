"""Runtime configuration, sourced entirely from environment variables.

Defaults let the app run locally (outside Docker) with no setup; the container
overrides them via docker-compose `environment:`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLAlchemy URL. In the container this is
    # sqlite:////app/data/catalog.db (four slashes == absolute path).
    database_url: str = "sqlite:///./data/catalog.db"

    # Directory holding the compiled React SPA (Dockerfile copies dist -> static).
    static_dir: str = "static"

    # Seed a few example users/repos on first run so a fresh hub isn't empty.
    seed_demo_data: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
