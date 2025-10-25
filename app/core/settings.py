from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    APP_NAME: str = "TimeTracker"
    APP_ENV: str = "dev"
    APP_DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8089

    UI_USERNAME: str = "admin"
    UI_PASSWORD_HASH: str = ""
    API_TOKEN: str = "change-me"

    DB_URL: str = "sqlite+aiosqlite:///./dev.db"

    CORS_ORIGINS: List[AnyHttpUrl] = []


settings = Settings()
