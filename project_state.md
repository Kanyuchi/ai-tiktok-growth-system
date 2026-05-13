# Project State — AI TikTok Growth System

## What's Working
- ETL pipeline: TikTok API → PostgreSQL → daily metrics snapshots
- Content engine: Canva thumbnail analysis → GPT-4o-mini caption generation
- Canva integration: design listing, MP4 export, off-brand detection
- TikTok poster: upload + publish flow with chunked upload
- Streamlit dashboard: KPIs, charts, leaderboard, CSV/HTML export
- **NEW**: RL module (Thompson Sampling) trained on 5 videos from watch matrix
- **NEW**: RL-integrated content engine (60% RL scoring, 30% heuristic, 10% exploration)
- **NEW**: Dashboard RL insights section (theme/hook charts, demographics, video comparison)
- **NEW**: Watch matrix data extracted from 22 TikTok Studio screenshots
- **NEW**: ffmpeg username overlay (`@thesoftupgrade1`) auto-applied on all MP4 exports
- **NEW**: Multi-account profiles — `--profile <name>` activates `.env.<name>` + `exports/<name>/` + `.oauth_session.<name>.json`. Commands: `new-profile`, `post-local`, `caption-video` (Claude Sonnet 4.6 vision → AI caption variants from profile niche)
- **NEW**: `@thetechmudhara` live (Sandbox app + ngrok OAuth + Private account workaround for unaudited-app gate). First post posted, analytics in. Niche pivoted to intentional-living-as-throughline after post-mortem revealed audience/content mismatch
- **NEW**: TikTok chunked-upload bug fixed (`_plan_chunks`: single chunk for files ≤ 64 MB; multi-chunk math respects "last chunk ≥ chunk_size" constraint)
- **NEW**: ffmpeg drawtext restored (homebrew-ffmpeg tap install — original homebrew/core ffmpeg 8.1 was stripped of libfreetype, silently breaking the @username overlay on both profiles)

## Broken / Incomplete
- No automated screenshot → watch matrix pipeline (manual extraction required)
- Mood arms untrained (no mood data extracted from screenshots yet)
- RL model has small sample (5 videos) — posteriors will improve with more data
- LinkedIn analytics module exists but separate from TikTok system
- Analytics/ETL (`run-daily`) is NOT profile-aware yet — DB schema is shared. Second account can post but not yet be tracked. Schema scoping by `account_open_id` is the next migration when needed.

## Key Decisions Made
- Thompson Sampling chosen over UCB/epsilon-greedy (better exploration-exploitation balance with small sample)
- Composite reward: 35% completion + 30% watch time + 20% views + 15% followers (completion weighted highest because it drives algorithm push)
- RL feeds into content engine at two points: page scoring and caption generation
- Watch matrix stored as JSON (not DB) — simple to update manually, no schema migration needed
- RL state persisted to `data/rl_state.json` — loaded on every content engine init

## Current Focus
- Using RL to optimise content selection: success theme × reframe_statement hook is the winning combo (0.764 reward)
- Addressing 2-second retention crisis across all videos
