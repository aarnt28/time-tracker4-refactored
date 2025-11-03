from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Environment-driven application configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data")
    TEMPLATES_DIR: Path | None = None
    STATIC_DIR: Path | None = None
    TZ: str = "America/Chicago"

    API_KEY: str = Field(default="", validation_alias=AliasChoices("API_KEY", "API_TOKEN"))
    API_TOKEN: str | None = None
    JWT_SECRET: str = "change-me"
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)
    AUTH_ALLOW_API_KEY: bool = True

    APP_SECRET: str = "dev-insecure-secret-change-me"
    UI_USERNAME: str = "admin"
    UI_PASSWORD: str = "change-me"
    UI_PASSWORD_HASH: str = ""
    SESSION_COOKIE_NAME: str = "tt_session"
    SESSION_MAX_AGE: int = 60 * 60 * 24 * 30

    DB_URL: str = Field(default="sqlite:///data/data.db", validation_alias="DATABASE_URL")

    HOST: str = "0.0.0.0"
    PORT: int = 8089

    GOOGLE_MAPS_API_KEY: str = ""
    GOOGLE_PLACES_AUTOCOMPLETE_URL: str = "https://places.googleapis.com/v1/places:autocomplete"
    GOOGLE_PLACES_DETAILS_URL: str = "https://places.googleapis.com/v1/places"
    GOOGLE_ADDRESS_VALIDATION_URL: str = "https://addressvalidation.googleapis.com/v1:validateAddress"
    GOOGLE_ADDRESS_VALIDATION_REGION_CODE: str = "US"

    S3_BUCKET: str | None = None
    R2_BUCKET: str | None = None
    S3_REGION: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None

    SENTRY_DSN: str | None = None

    RATE_LIMIT: str = "60/minute"

    def _resolve_path(self, base: Path | None, fallback: Path) -> Path:
        return base if base is not None else fallback

    @property
    def templates_dir(self) -> Path:
        return self._resolve_path(self.TEMPLATES_DIR, self.BASE_DIR / "app" / "templates")

    @property
    def static_dir(self) -> Path:
        return self._resolve_path(self.STATIC_DIR, self.BASE_DIR / "app" / "static")

    @property
    def s3_bucket_name(self) -> str | None:
        return self.S3_BUCKET or self.R2_BUCKET

    @property
    def API_KEY_VALUE(self) -> str:
        return self.API_KEY or (self.API_TOKEN or "")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, Iterable):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("ALLOWED_ORIGINS must be a comma separated string or list")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if settings.TEMPLATES_DIR is None:
        settings.TEMPLATES_DIR = settings.BASE_DIR / "app" / "templates"
    if settings.STATIC_DIR is None:
        settings.STATIC_DIR = settings.BASE_DIR / "app" / "static"
    settings.API_TOKEN = settings.API_KEY_VALUE
    return settings


settings = get_settings()
