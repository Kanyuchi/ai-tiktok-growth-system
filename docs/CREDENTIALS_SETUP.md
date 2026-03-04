# TikTok Credentials Setup (Official OAuth v2)

This guide gets you the credentials needed by this project:
- `TIKTOK_CLIENT_ID` (called `client_key` in TikTok docs)
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_ACCESS_TOKEN`
- `TIKTOK_REFRESH_TOKEN`
- `TIKTOK_REDIRECT_URI`

## 1. Create TikTok developer app
1. Go to TikTok for Developers and sign in: https://developers.tiktok.com/
2. Create a new app.
3. Open your app dashboard and copy:
   - Client key -> `TIKTOK_CLIENT_ID`
   - Client secret -> `TIKTOK_CLIENT_SECRET`

## 2. Configure Login Kit + Redirect URI
1. In your app products, enable **Login Kit**.
2. Add a redirect URI (example used in this project):
   - `http://localhost:3000/callback`
3. Put the same URI in your `.env`:
   - `TIKTOK_REDIRECT_URI=http://localhost:3000/callback`

Important: The redirect URI in `.env` must exactly match what is configured in TikTok app settings.

## 3. Request required scopes
Enable/approve these scopes for your app:
- `user.info.basic`
- `video.list`
- `video.insights`

Set in `.env`:
- `TIKTOK_SCOPES=user.info.basic,video.list,video.insights`

## 4. Generate authorization URL
Run:
```bash
python scripts/tiktok_cli.py auth-url
```

Open the printed URL, authorize your TikTok account, then copy the `code` from the redirect URL.

Optional easier flow:
1. Start callback listener:
```bash
python scripts/oauth_callback_server.py
```
2. Then open the auth URL.
3. After redirect, the server prints and stores the code in `.oauth_code.txt`.

## 5. Exchange code for tokens
Run:
```bash
python scripts/tiktok_cli.py exchange-code --code "PASTE_CODE_HERE" --save
```

This writes `TIKTOK_ACCESS_TOKEN` and `TIKTOK_REFRESH_TOKEN` into `.env`.

## 6. Validate API access
Run:
```bash
python scripts/tiktok_cli.py check --max-videos 5
```

If successful, proceed with:
```bash
python scripts/setup_db.py
python scripts/run_daily.py
streamlit run dashboard/app.py
```

## Token lifecycle
Per TikTok OAuth docs:
- Access token: ~24 hours
- Refresh token: up to 365 days

This project auto-refreshes on each pipeline run when `TIKTOK_REFRESH_TOKEN` is set and `TIKTOK_AUTO_REFRESH_ON_RUN=true`.

## Common issues
- `invalid_client`:
  - Client key/secret mismatch.
- `invalid_grant`:
  - Expired/used authorization code, or redirect URI mismatch.
- `scope_not_authorized`:
  - Scope not approved for the app yet.
