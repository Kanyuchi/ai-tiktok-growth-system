# AI TikTok Growth System

An automated TikTok analytics pipeline that pulls your video data daily, stores it in PostgreSQL, and surfaces performance insights through a live dashboard — so you always know what to post, when to post, and which content is growing your account.

---

## What it does

| Layer | What happens |
|---|---|
| **OAuth** | One-time TikTok login via PKCE-secured OAuth 2.0. Tokens auto-refresh on every run. |
| **Daily pipeline** | Runs at 09:00 every day (macOS launchd). Fetches all videos + metrics from TikTok API and upserts into PostgreSQL. |
| **Database** | PostgreSQL stores every video's metadata and a daily snapshot of its metrics — building a historical trend over time. |
| **Dashboard** | Streamlit dashboard always running at `http://localhost:8501`. Dark-themed, branded, updates automatically. |

---

## Dashboard features

- **6 KPI cards** — tracked posts, total views/likes/shares, avg engagement, best post
- **Views over time** — daily trend line, grows a new point every day automatically
- **Engagement by post** — top N posts ranked by your chosen metric (Views / Engagement / Share Rate / Likes / Comments)
- **Views vs Engagement scatter** — bubble size = shares, instantly shows what's both popular AND engaging
- **Content format mix** — donut chart (POV vs instructional vs standard)
- **Content leaderboard** — gold/silver/bronze ranked cards with engagement bars
- **Top hashtags** — which tags appear most across your best content
- **Daily metrics breakdown** — views, likes, shares, comments on one chart
- **Time period filter** — Last 7 / 30 / 90 days / All time
- **Top N slider** — show top 5 to 50 posts as your library grows

---

## Project structure

```
.
├── dashboard/
│   └── app.py                      # Streamlit dashboard
├── docs/
│   └── CREDENTIALS_SETUP.md        # TikTok Developer setup guide
├── images/
│   └── *.png                       # Logo assets
├── scripts/
│   ├── oauth_callback_server.py    # Listens for OAuth redirect on localhost:3000
│   ├── run_daily.py
│   ├── setup_db.py
│   ├── setup_wizard.py
│   └── tiktok_cli.py
├── sql/
│   └── schema.sql                  # PostgreSQL schema
├── src/
│   └── tiktok_ai_analytics/
│       ├── auth.py                 # PKCE OAuth client
│       ├── cli.py                  # CLI entry point
│       ├── config.py               # Settings from .env
│       ├── db.py                   # SQLAlchemy engine
│       ├── env_store.py            # Writes refreshed tokens back to .env
│       ├── kpis.py                 # engagement_rate, share_rate, retention_proxy
│       ├── recommendations.py      # Content scoring (MVP)
│       └── etl/
│           ├── pipeline.py         # Daily orchestration
│           └── tiktok_client.py    # TikTok API calls
├── .env                            # Secrets — never commit this
├── docker-compose.yml
└── pyproject.toml
```

---

## Setup

### 1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Start PostgreSQL
```bash
# Option A — Docker (recommended)
docker compose up -d postgres

# Option B — use your own Postgres, set DATABASE_URL in .env
```

### 3. Configure `.env`
```bash
cp .env.example .env
# Fill in: TIKTOK_CLIENT_ID, TIKTOK_CLIENT_SECRET, DATABASE_URL
```

### 4. TikTok OAuth (one-time)
```bash
# Step 1 — start callback listener
python scripts/oauth_callback_server.py &

# Step 2 — generate auth URL and open in browser
python -m tiktok_ai_analytics.cli auth-url

# Step 3 — after browser redirect, exchange code for tokens
python -m tiktok_ai_analytics.cli exchange-code --code "..." --save
```

Full guide: [docs/CREDENTIALS_SETUP.md](docs/CREDENTIALS_SETUP.md)

### 5. Initialize database
```bash
python -m tiktok_ai_analytics.cli setup-db
```

### 6. Run first pipeline pull
```bash
python -m tiktok_ai_analytics.cli run-daily
```

### 7. Launch dashboard
```bash
streamlit run dashboard/app.py
# Opens at http://localhost:8501
```

---

## Automation (macOS — already configured)

Two launchd agents run automatically:

| Agent | File | Schedule |
|---|---|---|
| Daily pipeline | `~/Library/LaunchAgents/com.fadzie.tiktok-daily.plist` | Every day at 09:00 |
| Dashboard server | `~/Library/LaunchAgents/com.fadzie.tiktok-dashboard.plist` | Always on, auto-restarts |

To reload after changes:
```bash
launchctl unload ~/Library/LaunchAgents/com.fadzie.tiktok-daily.plist
launchctl load   ~/Library/LaunchAgents/com.fadzie.tiktok-daily.plist
```

Logs:
```
~/Library/Logs/tiktok-daily.log
~/Library/Logs/tiktok-dashboard.log
```

---

## CLI reference

```bash
python -m tiktok_ai_analytics.cli setup-db
python -m tiktok_ai_analytics.cli auth-url
python -m tiktok_ai_analytics.cli exchange-code --code "..." --save
python -m tiktok_ai_analytics.cli refresh-token --save
python -m tiktok_ai_analytics.cli check --max-videos 5
python -m tiktok_ai_analytics.cli run-daily
python -m tiktok_ai_analytics.cli run-daily --max-videos 50 --no-persist-tokens
```

---

## Database schema

```sql
posts                  -- one row per video, metadata + extracted content signals
post_metrics_daily     -- one row per (video, date), raw metrics snapshot
experiments            -- A/B test tracking (future)
content_ideas          -- AI-generated post ideas (future)
```

---

## Token lifecycle

| Token | Expiry | Behaviour |
|---|---|---|
| Access token | 24 hours | Auto-refreshed at the start of every `run-daily` |
| Refresh token | ~1 year | When expired, re-run the OAuth flow once |

As long as the daily pipeline runs, you will never need to touch OAuth again.

---

## Metrics captured

| Metric | Source |
|---|---|
| views, likes, comments, shares | `/v2/video/list/` |
| saves, avg watch time, completion rate | `/v2/video/query/` (requires elevated access) |
| engagement rate | computed: `(likes+comments+shares+saves) / views` |
| share rate | computed: `shares / views` |
| retention proxy | computed: `avg_watch_time / duration` |

---

## Troubleshooting

**External drive `invalid distribution` errors:**
```bash
./scripts/cleanup_appledouble.sh
```

**Dashboard not loading:**
```bash
pkill -f "streamlit run"
streamlit run dashboard/app.py --server.port 8501 --server.headless true &
```

**Token expired:**
```bash
python -m tiktok_ai_analytics.cli refresh-token --save
```
