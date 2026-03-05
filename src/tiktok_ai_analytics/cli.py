from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .auth import TikTokAuthClient
from .canva_auth import CanvaAuthClient
from .canva_client import CanvaClient
from .content_engine import ContentEngine
from .config import load_settings
from .db import initialize_schema
from .env_store import upsert_env_values
from .etl.pipeline import run_daily_pipeline
from .etl.tiktok_client import TikTokClient

OAUTH_SESSION_FILE = Path(".oauth_session.json")
CANVA_SESSION_FILE = Path(".canva_session.json")


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


def _cmd_canva_auth_url(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.canva_client_id:
        print("Missing CANVA_CLIENT_ID in .env")
        return 1

    client = CanvaAuthClient(settings)
    code_verifier = client.generate_code_verifier()
    code_challenge = client.code_challenge_from_verifier(code_verifier)
    url, state = client.build_authorize_url(code_challenge=code_challenge)

    CANVA_SESSION_FILE.write_text(
        json.dumps({"state": state, "code_verifier": code_verifier}, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"State: {state}")
    print(f"Redirect URI: {settings.canva_redirect_uri}")
    print(f"Saved PKCE session to {CANVA_SESSION_FILE}")
    print("\nOpen this URL in your browser and authorize:")
    print(url)
    return 0


def _cmd_canva_exchange_code(args: argparse.Namespace) -> int:
    settings = load_settings()
    client = CanvaAuthClient(settings)

    code_verifier = args.code_verifier
    if not code_verifier and CANVA_SESSION_FILE.exists():
        session_data = json.loads(CANVA_SESSION_FILE.read_text(encoding="utf-8"))
        code_verifier = session_data.get("code_verifier")

    if not code_verifier:
        print("Missing PKCE code_verifier. Run `canva-auth-url` first.")
        return 1

    bundle = client.exchange_code_for_tokens(code=args.code, code_verifier=code_verifier)
    print("Canva access token received.")
    print(f"expires_in: {bundle.expires_in}")

    if args.save:
        upsert_env_values({
            "CANVA_ACCESS_TOKEN": bundle.access_token,
            "CANVA_REFRESH_TOKEN": bundle.refresh_token,
        })
        print("Saved CANVA_ACCESS_TOKEN and CANVA_REFRESH_TOKEN into .env")
    return 0


def _cmd_canva_refresh_token(args: argparse.Namespace) -> int:
    settings = load_settings()
    refresh_token = args.refresh_token or settings.canva_refresh_token
    if not refresh_token:
        print("Missing refresh token. Set CANVA_REFRESH_TOKEN in .env or pass --refresh-token")
        return 1

    client = CanvaAuthClient(settings)
    bundle = client.refresh_access_token(refresh_token=refresh_token)
    print("Canva token refreshed.")
    print(f"expires_in: {bundle.expires_in}s (~{bundle.expires_in // 3600}h)")

    if args.save:
        upsert_env_values({
            "CANVA_ACCESS_TOKEN": bundle.access_token,
            "CANVA_REFRESH_TOKEN": bundle.refresh_token,
        })
        print("Saved CANVA_ACCESS_TOKEN and CANVA_REFRESH_TOKEN into .env")
    return 0


def _cmd_canva_list_designs(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.canva_access_token:
        print("Missing CANVA_ACCESS_TOKEN — run `canva-auth-url` first.")
        return 1

    client = CanvaClient(access_token=settings.canva_access_token, settings=settings)
    designs = client.list_designs(query=args.query, limit=args.limit)

    if not designs:
        print("No designs found.")
        return 0

    print(f"{'ID':<30} {'Updated':<12} {'Title'}")
    print("-" * 80)
    for d in designs:
        updated = d.updated_at.strftime("%Y-%m-%d") if d.updated_at else "—"
        print(f"{d.design_id:<30} {updated:<12} {d.title}")

    print(f"\n{len(designs)} design(s) returned.")
    return 0


def _cmd_canva_export(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.canva_access_token:
        print("Missing CANVA_ACCESS_TOKEN — run `canva-auth-url` first.")
        return 1

    client = CanvaClient(access_token=settings.canva_access_token, settings=settings)
    print(f"Exporting design {args.design_id} as {args.format} …")
    output_path = client.export_design(
        design_id=args.design_id,
        export_format=args.format,
        output_dir=Path(args.output_dir),
    )
    print(f"Saved to: {output_path}")
    return 0


def _cmd_content_brief(args: argparse.Namespace) -> int:
    engine = ContentEngine()
    print("Analysing reels and performance data...")
    brief = engine.generate_daily_brief(design_id=args.design_id or None)

    print("\n" + "═" * 60)
    print(f"  TODAY'S CONTENT BRIEF")
    print("═" * 60)
    print(f"  Reel page  : #{brief.page_index} of 367")
    print(f"  Theme      : {brief.theme}")
    print(f"  Mood       : {brief.mood}")
    print(f"  Hook idea  : {brief.hook_suggestion}")
    print(f"  Why chosen : {brief.rationale}")
    print("─" * 60)
    print(f"\nCAPTION:\n{brief.caption}")
    print(f"\n{brief.hashtags}")
    print("═" * 60)
    print(f"\nThumbnail preview:\n{brief.thumbnail_url}\n")

    if args.export:
        from pathlib import Path
        from .canva_client import CanvaClient
        settings = load_settings()
        client = CanvaClient(access_token=settings.canva_access_token, settings=settings)
        print(f"Exporting page {brief.page_index} as mp4...")
        out = client.export_design(
            design_id=args.design_id or ContentEngine.DESIGN_ID,
            export_format="mp4",
            output_dir=Path("exports"),
            pages=[brief.page_index],
        )
        print(f"Saved: {out}")

    return 0


def _cmd_post_reel(args: argparse.Namespace) -> int:
    """Generate a content brief, export the chosen page, then post to TikTok."""
    from pathlib import Path
    from .canva_client import CanvaClient
    from .content_engine import ContentEngine
    from .tiktok_poster import TikTokPoster

    settings = load_settings()

    if not settings.tiktok_access_token:
        print("Missing TIKTOK_ACCESS_TOKEN — run `auth-url` and `exchange-code` first.")
        return 1
    if not settings.canva_access_token:
        print("Missing CANVA_ACCESS_TOKEN — run `canva-auth-url` first.")
        return 1

    # Step 1: Generate content brief
    print("Step 1/3 — Generating content brief...")
    engine = ContentEngine(settings=settings)
    brief = engine.generate_daily_brief(design_id=args.design_id or None)

    full_caption = brief.caption + "\n\n" + brief.hashtags

    print("\n" + "═" * 60)
    print("  CONTENT BRIEF")
    print("═" * 60)
    print(f"  Reel page  : #{brief.page_index} of 367")
    print(f"  Theme      : {brief.theme}")
    print(f"  Mood       : {brief.mood}")
    print("─" * 60)
    print(f"\nCAPTION:\n{brief.caption}")
    print(f"\n{brief.hashtags}")
    print("═" * 60 + "\n")

    if args.dry_run:
        print("[DRY RUN] Skipping export and post. Brief generated successfully.")
        return 0

    # Step 2: Export the chosen page as MP4
    print(f"Step 2/3 — Exporting page #{brief.page_index} from Canva...")
    canva = CanvaClient(access_token=settings.canva_access_token, settings=settings)
    design_id = args.design_id or ContentEngine.DESIGN_ID
    video_path = canva.export_design(
        design_id=design_id,
        export_format="mp4",
        output_dir=Path("exports"),
        pages=[brief.page_index],
    )
    print(f"Video saved: {video_path}")

    # Step 3: Post to TikTok
    print("Step 3/3 — Posting to TikTok...")
    poster = TikTokPoster(access_token=settings.tiktok_access_token, settings=settings)
    result = poster.post_video(
        video_path=video_path,
        caption=full_caption,
        privacy_level=args.privacy,
    )

    print("\n" + "✓" * 60)
    print(f"  Posted! publish_id: {result.publish_id}")
    print(f"  Status: {result.status}")
    print("✓" * 60)
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

    # ── Canva commands ────────────────────────────────────────────────────────
    sub.add_parser("canva-auth-url", help="Generate Canva OAuth authorization URL")

    p_canva_ex = sub.add_parser("canva-exchange-code", help="Exchange Canva OAuth code for tokens")
    p_canva_ex.add_argument("--code", required=True, help="OAuth code from Canva redirect")
    p_canva_ex.add_argument("--code-verifier", default=None)
    p_canva_ex.add_argument("--save", action="store_true", help="Save tokens into .env")

    p_canva_refresh = sub.add_parser("canva-refresh-token", help="Refresh Canva access token")
    p_canva_refresh.add_argument("--refresh-token", default=None, help="Override refresh token")
    p_canva_refresh.add_argument("--save", action="store_true", help="Save refreshed tokens into .env")

    p_canva_list = sub.add_parser("canva-list-designs", help="List Canva designs")
    p_canva_list.add_argument("--query", default=None, help="Search query")
    p_canva_list.add_argument("--limit", type=int, default=20)

    p_canva_export = sub.add_parser("canva-export", help="Export a Canva design")
    p_canva_export.add_argument("--design-id", required=True)
    p_canva_export.add_argument("--format", default="mp4", choices=["mp4", "gif", "jpg", "png", "pdf"])
    p_canva_export.add_argument("--output-dir", default="exports")

    p_brief = sub.add_parser("content-brief", help="Pick today's reel + generate caption & hashtags")
    p_brief.add_argument("--design-id", default=None, help="Override Canva design ID")
    p_brief.add_argument("--export", action="store_true", help="Also export the chosen page as MP4")

    p_post = sub.add_parser(
        "post-reel",
        help="Full pipeline: generate brief → export page → post to TikTok",
    )
    p_post.add_argument("--design-id", default=None, help="Override Canva design ID")
    p_post.add_argument(
        "--privacy",
        default="PUBLIC_TO_EVERYONE",
        choices=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"],
        help="TikTok post privacy level",
    )
    p_post.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the brief only — skip export and posting",
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
        "canva-auth-url": _cmd_canva_auth_url,
        "canva-exchange-code": _cmd_canva_exchange_code,
        "canva-refresh-token": _cmd_canva_refresh_token,
        "canva-list-designs": _cmd_canva_list_designs,
        "canva-export": _cmd_canva_export,
        "content-brief": _cmd_content_brief,
        "post-reel": _cmd_post_reel,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
