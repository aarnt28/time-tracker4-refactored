"""Human-friendly configuration loader.

The ``Settings`` class centralises every environment variable we rely on. That
means anyone inspecting the project can quickly answer the questions:

*What:* Which settings exist and what do they control?
*When:* They are read once at startup when the module is imported.
*Why:* Centralising configuration prevents magic strings scattered all over the
codebase.
*How:* Each attribute uses ``os.getenv`` with a sensible default so the app can
boot in development without extra setup.
"""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    # Base folders keep file-path building consistent. ``BASE_DIR`` points to
    # the repository root so we can easily derive template/static directories.
    BASE_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
    TEMPLATES_DIR = BASE_DIR / "app" / "templates"
    STATIC_DIR = BASE_DIR / "app" / "static"
    TZ = os.getenv("TZ", "America/Chicago")

    # ---- API (headless) authentication
    # ``API_TOKEN`` acts like a master key for machine-to-machine calls.
    API_TOKEN = os.getenv("API_TOKEN", "")  # X-API-Key must match this (if set)

    # ---- UI (browser) authentication
    # Cookie/session secret. MUST be long & random in production.
    APP_SECRET = os.getenv("APP_SECRET", "dev-insecure-secret-change-me")
    # Simple single-user creds for the UI (browser) login so teams can test the
    # portal quickly.
    UI_USERNAME = os.getenv("UI_USERNAME", "admin")
    # Store a bcrypt hash if you have one; otherwise fallback to plain.
    # If UI_PASSWORD_HASH is set, it takes precedence over UI_PASSWORD.
    UI_PASSWORD = os.getenv("UI_PASSWORD", "change-me")
    UI_PASSWORD_HASH = os.getenv("UI_PASSWORD_HASH", "")  # e.g. $2b$12$...

    # Cookie settings define how long login sessions stick around in the
    # browser.
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tt_session")
    SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", "2592000"))  # 30 days in seconds

    # Database URL defaults to SQLite under the /data volume so Docker demos
    # work out-of-the-box.
    DB_URL = os.getenv("DB_URL", f"sqlite:///{DATA_DIR}/data.db")

    # App binding (container listens on 0.0.0.0:8089; host/Windows maps via compose)
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8089"))

    # Google Maps JavaScript & Places APIs (client location preview + address tools)
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_PLACES_AUTOCOMPLETE_URL = os.getenv(
        "GOOGLE_PLACES_AUTOCOMPLETE_URL",
        "https://places.googleapis.com/v1/places:autocomplete",
    )
    GOOGLE_PLACES_DETAILS_URL = os.getenv(
        "GOOGLE_PLACES_DETAILS_URL",
        "https://places.googleapis.com/v1/places",
    )
    GOOGLE_ADDRESS_VALIDATION_URL = os.getenv(
        "GOOGLE_ADDRESS_VALIDATION_URL",
        "https://addressvalidation.googleapis.com/v1:validateAddress",
    )
    GOOGLE_ADDRESS_VALIDATION_REGION_CODE = os.getenv(
        "GOOGLE_ADDRESS_VALIDATION_REGION_CODE",
        "US",
    )


# Instantiating here means importing ``settings`` anywhere instantly gives you
# access to the configured values without rebuilding the object each time.
settings = Settings()
