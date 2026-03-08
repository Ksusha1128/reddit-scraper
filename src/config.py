"""
Application configuration with validation via Pydantic.

All settings are loaded from environment variables or .env file.
No secrets should ever be hardcoded or passed via CLI arguments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class ScraperSettings(BaseSettings):
    """Reddit scraper HTTP settings."""

    user_agent: str = (
        "CoupleAppReviewScraper/2.0 "
        "(compatible; research; +https://github.com/ksanjeev284/reddit-universal-scraper)"
    )
    request_timeout: int = Field(default=15, ge=1, le=120)
    cooldown_min: float = Field(default=0.5, ge=0.1)
    cooldown_max: float = Field(default=1.5, ge=0.3)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_backoff_factor: float = Field(default=2.0, ge=1.0)

    mirrors: list[str] = [
        "https://old.reddit.com",
        "https://redlib.catsarch.com",
        "https://redlib.vsls.cz",
        "https://r.nf",
        "https://libreddit.northboot.xyz",
        "https://redlib.tux.pizza",
    ]

    model_config = {"env_prefix": "SCRAPER_"}


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str = Field(default="sqlite+aiosqlite:///data/reddit_scraper.db")
    echo: bool = False
    pool_size: int = Field(default=5, ge=1)

    model_config = {"env_prefix": "DB_"}


class NotificationSettings(BaseSettings):
    """Notification channels — secrets loaded exclusively from env vars."""

    discord_webhook_url: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None

    model_config = {"env_prefix": "NOTIFY_"}


class DashboardSettings(BaseSettings):
    """Dashboard UI settings."""

    host: str = "127.0.0.1"
    port: int = Field(default=8501, ge=1024, le=65535)

    model_config = {"env_prefix": "DASHBOARD_"}


class APISettings(BaseSettings):
    """REST API settings."""

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    allowed_origins: list[str] = ["http://localhost:8501"]
    rate_limit_per_minute: int = Field(default=60, ge=1)

    model_config = {"env_prefix": "API_"}


class Settings(BaseSettings):
    """Root settings — aggregates all sub-settings."""

    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Field(default=None)  # type: ignore[assignment]

    scraper: ScraperSettings = ScraperSettings()
    database: DatabaseSettings = DatabaseSettings()
    notifications: NotificationSettings = NotificationSettings()
    dashboard: DashboardSettings = DashboardSettings()
    api: APISettings = APISettings()

    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    model_config = {"env_prefix": "APP_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("data_dir", mode="before")
    @classmethod
    def _default_data_dir(cls, v: Path | None) -> Path:
        if v is not None:
            return Path(v)
        # Default — will be relative to base_dir, set in model_post_init
        return Path(__file__).resolve().parent.parent / "data"

    def model_post_init(self, __context: Any) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Singleton — import `settings` everywhere
settings = Settings()
