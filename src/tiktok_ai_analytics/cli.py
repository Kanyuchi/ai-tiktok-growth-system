from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .auth import TikTokAuthClient
from .config import load_settings
from .db import initialize_schema
from .env_store import upsert_env_values
from .etl.pipeline import run_daily_pipeline
from .etl.tiktok_client import TikTokClient

OAUTH_SESSION_FILE = Path(".oauth_session.json")


def setup_db() -> None:
    initialize_schema()
    print("Database schema initialized.")


def run_daily() -> None:
    run_daily_pipeline()
    print("Daily pipeline completed.")


def _cmd_setup_db(_: argparse.Namespace) -> int:
    setup_db()
    return 0


def _cmd_auth_url(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.tiktok_client_id:
        print("Missing TIKTOK_CLIENT_ID in .env")
        return 1

    client = TikTokAuthClient(settings)
    code_verifier = client.generate_code_verifier()
    code_challenge = client.code_challenge_from_verifier(code_verifier)
    url, state = client.build_authorize_url(state=args.state, code_challenge=code_challenge)

    OAUTH_SESSION_FILE.write_text(
        json.dumps(
            {
                "state": state,
                "code_verifier": code_verifier,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"State: {state}")
    print("PKCE enabled: code_challenge_method=S256")
    print(f"Saved PKCE session to {OAUTH_SESSION_FILE}")
    print("Open this URL in your browser and authorize:")
    print(url)
    return 0


def _cmd_exchange_code(args: argparse.Namespace) -> int:
    settings = load_settings()
    client = TikTokAuthClient(settings)
    code_verifier = args.code_verifier
    if not code_verifier and OAUTH_SESSION_FILE.exists():
        session_data = json.loads(OAUTH_SESSION_FILE.read_text(encoding="utf-8"))
        code_verifier = session_data.get("code_verifier")

    if not code_verifier:
        print(
            "Missing PKCE code_verifier. Run `auth-url` first (recommended), "
            "or pass --code-verifier explicitly."
        )
        return 1

    bundle = client.exchange_code_for_tokens(code=args.code, code_verifier=code_verifier)

    print("Access token received.")
    print(f"open_id: {bundle.open_id}")
    print(f"scope: {bundle.scope}")
    print(f"expires_in: {bundle.expires_in}")

    if args.save:
        upsert_env_values(
            {
                "TIKTOK_ACCESS_TOKEN": bundle.access_token,
                "TIKTOK_REFRESH_TOKEN": bundle.refresh_token,
            }
        )
        print("Saved TIKTOK_ACCESS_TOKEN and TIKTOK_REFRESH_TOKEN into .env")

    return 0


def _cmd_refresh_token(args: argparse.Namespace) -> int:
    settings = load_settings()
    refresh_token = args.refresh_token or settings.tiktok_refresh_token
    if not refresh_token:
        print("Missing refresh token. Set TIKTOK_REFRESH_TOKEN in .env or pass --refresh-token")
        return 1

    client = TikTokAuthClient(settings)
    bundle = client.refresh_access_token(refresh_token=refresh_token)

    print("Token refreshed.")
    print(f"expires_in: {bundle.expires_in}")

    if args.save:
        upsert_env_values(
            {
                "TIKTOK_ACCESS_TOKEN": bundle.access_token,
                "TIKTOK_REFRESH_TOKEN": bundle.refresh_token,
            }
        )
        print("Saved refreshed tokens into .env")

    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.tiktok_access_token:
        print("Missing TIKTOK_ACCESS_TOKEN in .env")
        return 1

    client = TikTokClient(access_token=settings.tiktok_access_token, settings=settings)
    videos = client.list_all_videos(max_results=max(args.max_videos, 1))
    print(f"TikTok API connection OK. Retrieved {len(videos)} video(s).")
    return 0


def _cmd_run_daily(args: argparse.Namespace) -> int:
    run_daily_pipeline(max_videos=args.max_videos, persist_tokens=not args.no_persist_tokens)
    print("Daily pipeline completed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TikTok AI Analytics CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup-db", help="Initialize PostgreSQL schema")

    p_auth = sub.add_parser("auth-url", help="Generate TikTok OAuth authorization URL")
    p_auth.add_argument("--state", default=None, help="Optional custom state value")

    p_exchange = sub.add_parser("exchange-code", help="Exchange OAuth code for tokens")
    p_exchange.add_argument("--code", required=True, help="OAuth code from TikTok redirect")
    p_exchange.add_argument(
        "--code-verifier",
        default=None,
        help="Optional PKCE verifier (auto-loaded from .oauth_session.json when omitted)",
    )
    p_exchange.add_argument("--save", action="store_true", help="Save tokens into .env")

    p_refresh = sub.add_parser("refresh-token", help="Refresh access token")
    p_refresh.add_argument("--refresh-token", default=None, help="Override refresh token")
    p_refresh.add_argument("--save", action="store_true", help="Save refreshed tokens into .env")

    p_check = sub.add_parser("check", help="Validate TikTok API connectivity")
    p_check.add_argument("--max-videos", type=int, default=5, help="Number of videos to fetch")

    p_run = sub.add_parser("run-daily", help="Run daily ETL pipeline")
    p_run.add_argument("--max-videos", type=int, default=None, help="Override max videos for this run")
    p_run.add_argument(
        "--no-persist-tokens",
        action="store_true",
        help="Do not write refreshed tokens back to .env",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "setup-db": _cmd_setup_db,
        "auth-url": _cmd_auth_url,
        "exchange-code": _cmd_exchange_code,
        "refresh-token": _cmd_refresh_token,
        "check": _cmd_check,
        "run-daily": _cmd_run_daily,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
