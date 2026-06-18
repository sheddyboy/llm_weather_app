"""Application settings, loaded from environment / `.env` via pydantic-settings.

Every variable the project will eventually need is declared here up front (see
`.env.example` and ARCHITECTURE_DESIGN_DOCUMENT.md), so later batches wire in
behavior without touching configuration plumbing.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed view over the process environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres@localhost:5432/weatherapp"
    database_url_test: str = (
        "postgresql+asyncpg://postgres@localhost:5432/weatherapp_test"
    )

    # --- Cache ---
    cache_backend: str = "memory"  # "memory" | "redis"
    redis_url: str = "redis://localhost:6379/0"

    # --- OpenWeatherMap ---
    openweather_api_key: str = ""

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # --- YouTube ---
    youtube_api_key: str = ""
    enable_youtube: bool = True

    # --- Google Places ---
    google_places_api_key: str = ""
    enable_places: bool = True

    # --- CORS ---
    # Origins allowed to call the API from a browser (the Next.js frontend in dev).
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- Logging ---
    log_level: str = "INFO"

    # --- /meta endpoint ---
    meta_name: str = "Weather App"
    meta_description: str = (
        "Real-time weather forecasts and local insights for your city, powered by AI."
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance (read the environment once)."""
    return Settings()


settings = get_settings()
