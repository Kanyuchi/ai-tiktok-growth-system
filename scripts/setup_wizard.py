from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tiktok_ai_analytics.env_store import upsert_env_values


def ask(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw or default


def main() -> None:
    print("TikTok AI Analytics - Setup Wizard")
    print("This will create/update your .env file.")

    values = {
        "APP_ENV": ask("APP_ENV", "dev"),
        "TIMEZONE": ask("TIMEZONE", "Europe/Berlin"),
        "DATABASE_URL": ask(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/tiktok_ai_analytics",
        ),
        "TIKTOK_CLIENT_ID": ask("TIKTOK_CLIENT_ID", ""),
        "TIKTOK_CLIENT_SECRET": ask("TIKTOK_CLIENT_SECRET", ""),
        "TIKTOK_REDIRECT_URI": ask("TIKTOK_REDIRECT_URI", "http://localhost:3000/callback"),
        "TIKTOK_SCOPES": ask(
            "TIKTOK_SCOPES",
            "user.info.basic,video.list,video.insights",
        ),
        "TIKTOK_TOKEN_URL": ask("TIKTOK_TOKEN_URL", "https://open.tiktokapis.com/v2/oauth/token/"),
        "TIKTOK_API_BASE_URL": ask("TIKTOK_API_BASE_URL", "https://open.tiktokapis.com/v2"),
        "TIKTOK_AUTO_REFRESH_ON_RUN": ask("TIKTOK_AUTO_REFRESH_ON_RUN", "true"),
        "TIKTOK_REQUEST_TIMEOUT_SECONDS": ask("TIKTOK_REQUEST_TIMEOUT_SECONDS", "30"),
        "TIKTOK_PAGE_SIZE": ask("TIKTOK_PAGE_SIZE", "20"),
        "TIKTOK_MAX_VIDEOS_PER_RUN": ask("TIKTOK_MAX_VIDEOS_PER_RUN", "200"),
    }

    upsert_env_values(values=values, env_path=PROJECT_ROOT / ".env")
    print("Saved .env. Next: run auth URL command to generate tokens.")


if __name__ == "__main__":
    main()
