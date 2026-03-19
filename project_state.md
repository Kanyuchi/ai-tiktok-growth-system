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

## Broken / Incomplete
- No automated screenshot → watch matrix pipeline (manual extraction required)
- Mood arms untrained (no mood data extracted from screenshots yet)
- RL model has small sample (5 videos) — posteriors will improve with more data
- LinkedIn analytics module exists but separate from TikTok system

## Key Decisions Made
- Thompson Sampling chosen over UCB/epsilon-greedy (better exploration-exploitation balance with small sample)
- Composite reward: 35% completion + 30% watch time + 20% views + 15% followers (completion weighted highest because it drives algorithm push)
- RL feeds into content engine at two points: page scoring and caption generation
- Watch matrix stored as JSON (not DB) — simple to update manually, no schema migration needed
- RL state persisted to `data/rl_state.json` — loaded on every content engine init

## Current Focus
- Using RL to optimise content selection: success theme × reframe_statement hook is the winning combo (0.764 reward)
- Addressing 2-second retention crisis across all videos
