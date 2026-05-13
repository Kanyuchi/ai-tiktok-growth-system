# Multi-Account Profiles

The CLI supports multiple TikTok accounts via profiles. Each profile is a named
configuration that maps to its own env file, OAuth session, and folders.

| Resource | Default account | Profile `<name>` |
|---|---|---|
| Env file | `.env` | `.env.<name>` |
| OAuth session | `.oauth_session.json` | `.oauth_session.<name>.json` |
| Exports dir | `exports/` | `exports/<name>/` |
| Data dir | `data/` | `data/<name>/` |

Profiles are activated by passing `--profile <name>` to the CLI **before** the
subcommand. Without `--profile`, the legacy single-account layout is used.

All `.env.*` files and `.oauth_session.*.json` files are gitignored.

## Adding a new account

### 1. Scaffold the profile

```bash
python scripts/tiktok_cli.py new-profile \
    --name thetechmudhara \
    --handle @thetechmudhara \
    --niche "Tech and AI, Drone flying videos, Travel, Fashion"
```

This creates:
- `.env.thetechmudhara` (with empty credential placeholders)
- `exports/thetechmudhara/`
- `data/thetechmudhara/profile.md`

### 2. Create a TikTok developer app

The original luxury account already uses one TikTok dev app. The new account
needs its own to keep OAuth state and rate limits separate.

1. Go to <https://developers.tiktok.com/apps> and create a new app.
2. Add `http://localhost:3000/callback` as a redirect URI.
3. Enable scopes: `user.info.basic`, `video.list`, `video.insights`, **`video.publish`**.
4. Copy the client key and secret into `.env.thetechmudhara`:
   ```
   TIKTOK_CLIENT_ID=...
   TIKTOK_CLIENT_SECRET=...
   ```

### 3. OAuth the new account

```bash
python scripts/tiktok_cli.py --profile thetechmudhara auth-url
# open the printed URL in a browser, log into the NEW TikTok account, authorise.
# the browser redirects to localhost:3000/callback?code=...&state=...
# copy the code value (or use scripts/oauth_callback_server.py to capture it).

python scripts/tiktok_cli.py --profile thetechmudhara exchange-code \
    --code <code> --save
```

`--save` writes `TIKTOK_ACCESS_TOKEN` and `TIKTOK_REFRESH_TOKEN` back into the
**profile-specific** env file (`.env.thetechmudhara`).

### 4. Post a local MP4

```bash
python scripts/tiktok_cli.py --profile thetechmudhara post-local \
    --video exports/thetechmudhara/clip1.mp4 \
    --caption "drone shot over the alps ☁️ #dronefootage #travel"
```

Useful flags:
- `--caption-file path.txt` — load caption from a file instead of inline
- `--privacy SELF_ONLY` — post privately first to QA, then re-post public
- `--no-overlay` — skip burning the username overlay
- `--dry-run` — print what would happen, don't upload

### 5. Refresh tokens later

TikTok access tokens expire. Refresh with:

```bash
python scripts/tiktok_cli.py --profile thetechmudhara refresh-token --save
```

## What this profile does NOT do (yet)

- Analytics/ETL (`run-daily`) is not profile-aware — the DB schema is shared
  with the luxury account. If you want analytics for the new account, we'll
  need to add an account scope to the schema. Deferred until you decide the
  new account is worth tracking.
- The Streamlit dashboard reads from the shared DB + the default RL state,
  so it currently only reflects the luxury account.
- Canva integration is not wired per-profile because the new account uses
  external videos, not Canva designs.
