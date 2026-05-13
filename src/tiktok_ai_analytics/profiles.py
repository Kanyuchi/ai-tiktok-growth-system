from __future__ import annotations

"""
Multi-account profile support.

A "profile" is a named TikTok account configuration. Each profile maps to:
  - .env.<profile>           (TikTok creds, tokens, username overlay text)
  - .oauth_session.<profile>.json
  - exports/<profile>/        (per-account video exports + caption files)
  - data/<profile>/           (per-account local state, if needed)

Activate with `--profile <name>` on the CLI or by setting TIKTOK_PROFILE=<name>.
Without a profile, the legacy single-account layout is used (.env, exports/, data/).
"""

import os
from pathlib import Path

from dotenv import load_dotenv


def active_profile() -> str | None:
    """Return the currently active profile name, or None for the legacy account."""
    value = os.environ.get("TIKTOK_PROFILE", "").strip()
    return value or None


def env_file(profile: str | None) -> Path:
    return Path(f".env.{profile}") if profile else Path(".env")


def oauth_session_file(profile: str | None) -> Path:
    if profile:
        return Path(f".oauth_session.{profile}.json")
    return Path(".oauth_session.json")


def exports_dir(profile: str | None) -> Path:
    return Path("exports") / profile if profile else Path("exports")


def data_dir(profile: str | None) -> Path:
    return Path("data") / profile if profile else Path("data")


def activate(profile: str) -> Path:
    """Load .env.<profile> over the current environment and mark it active.

    Raises FileNotFoundError if the profile env file is missing — that means
    the profile has not been scaffolded yet (`new-profile --name <profile>`).
    """
    path = env_file(profile)
    if not path.exists():
        raise FileNotFoundError(
            f"Profile env file not found: {path}. "
            f"Run `python -m tiktok_ai_analytics.cli new-profile --name {profile}` first."
        )
    load_dotenv(path, override=True)
    os.environ["TIKTOK_PROFILE"] = profile
    return path


PROFILE_ENV_TEMPLATE = """# TikTok profile: {profile}
# Handle : {handle}
# Niche  : {niche}
#
# Created by `new-profile`. Fill in the TikTok dev-app credentials below,
# then run:
#     python -m tiktok_ai_analytics.cli --profile {profile} auth-url
#     python -m tiktok_ai_analytics.cli --profile {profile} exchange-code --code <code> --save

TIKTOK_PROFILE={profile}
TIKTOK_USERNAME={handle}

# TikTok dev app credentials (create a NEW app at https://developers.tiktok.com/apps)
TIKTOK_CLIENT_ID=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=http://localhost:3000/callback
TIKTOK_SCOPES=user.info.basic,video.list,video.insights,video.publish

# Filled in automatically by `exchange-code --save` / `refresh-token --save`
TIKTOK_ACCESS_TOKEN=
TIKTOK_REFRESH_TOKEN=

# Runtime
TIKTOK_AUTO_REFRESH_ON_RUN=true
TIKTOK_REQUEST_TIMEOUT_SECONDS=30
TIKTOK_PAGE_SIZE=20
TIKTOK_MAX_VIDEOS_PER_RUN=200
"""


def scaffold(profile: str, handle: str, niche: str) -> dict[str, Path]:
    """Create the per-profile env file and directories. Idempotent (won't overwrite env)."""
    env_path = env_file(profile)
    exports_path = exports_dir(profile)
    data_path = data_dir(profile)

    exports_path.mkdir(parents=True, exist_ok=True)
    data_path.mkdir(parents=True, exist_ok=True)

    if not env_path.exists():
        env_path.write_text(
            PROFILE_ENV_TEMPLATE.format(profile=profile, handle=handle, niche=niche),
            encoding="utf-8",
        )

    notes_path = data_path / "profile.md"
    if not notes_path.exists():
        notes_path.write_text(
            f"# {handle}\n\n**Niche:** {niche}\n\nCreated by `new-profile`.\n",
            encoding="utf-8",
        )

    return {"env": env_path, "exports": exports_path, "data": data_path, "notes": notes_path}
