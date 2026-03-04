from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv(override=False)


def _to_bool(raw: str, default: bool) -> bool:
    if raw is None:
        return default
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}


def _to_int(raw: str, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str
    timezone: str

    database_url: str

    tiktok_client_id: str
    tiktok_client_secret: str
    tiktok_access_token: str
    tiktok_refresh_token: str
    tiktok_token_url: str
    tiktok_api_base_url: str
    tiktok_redirect_uri: str
    tiktok_scopes: str

    tiktok_auto_refresh_on_run: bool
    tiktok_request_timeout_seconds: int
    tiktok_page_size: int
    tiktok_max_videos_per_run: int

    # Canva Connect API
    canva_client_id: str
    canva_client_secret: str
    canva_redirect_uri: str
    canva_scopes: str
    canva_access_token: str
    canva_refresh_token: str


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        timezone=os.getenv("TIMEZONE", "Europe/Berlin"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/tiktok_ai_analytics",
        ),
        tiktok_client_id=os.getenv("TIKTOK_CLIENT_ID", ""),
        tiktok_client_secret=os.getenv("TIKTOK_CLIENT_SECRET", ""),
        tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN", ""),
        tiktok_refresh_token=os.getenv("TIKTOK_REFRESH_TOKEN", ""),
        tiktok_token_url=os.getenv(
            "TIKTOK_TOKEN_URL", "https://open.tiktokapis.com/v2/oauth/token/"
        ),
        tiktok_api_base_url=os.getenv("TIKTOK_API_BASE_URL", "https://open.tiktokapis.com/v2"),
        tiktok_redirect_uri=os.getenv("TIKTOK_REDIRECT_URI", "http://localhost:3000/callback"),
        tiktok_scopes=os.getenv(
            "TIKTOK_SCOPES",
            "user.info.basic,video.list,video.insights",
        ),
        tiktok_auto_refresh_on_run=_to_bool(os.getenv("TIKTOK_AUTO_REFRESH_ON_RUN"), True),
        tiktok_request_timeout_seconds=_to_int(
            os.getenv("TIKTOK_REQUEST_TIMEOUT_SECONDS"), 30
        ),
        tiktok_page_size=_to_int(os.getenv("TIKTOK_PAGE_SIZE"), 20),
        tiktok_max_videos_per_run=_to_int(os.getenv("TIKTOK_MAX_VIDEOS_PER_RUN"), 200),
        canva_client_id=os.getenv("CANVA_CLIENT_ID", ""),
        canva_client_secret=os.getenv("CANVA_CLIENT_SECRET", ""),
        canva_redirect_uri=os.getenv("CANVA_REDIRECT_URI", "http://127.0.0.1:3001/callback"),
        canva_scopes=os.getenv(
            "CANVA_SCOPES",
            "design:meta:read design:content:read design:content:write asset:read asset:write",
        ),
        canva_access_token=os.getenv("CANVA_ACCESS_TOKEN", ""),
        canva_refresh_token=os.getenv("CANVA_REFRESH_TOKEN", ""),
    )


settings = load_settings()
