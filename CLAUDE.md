# Project: AI TikTok Growth System

## What This Is
End-to-end AI-powered TikTok content analytics and automated posting system. Analyses video performance, generates optimised captions using AI vision + GPT-4o-mini, exports reels from Canva designs, and posts to TikTok. Now includes a reinforcement learning layer that learns from real watch matrix data (extracted from TikTok Studio) to optimise content selection and caption generation.

## Stack / Tech
- Python 3.11+, SQLAlchemy 2.0, PostgreSQL, Streamlit (dashboard), Plotly
- APIs: TikTok Open Platform (OAuth PKCE), Canva Connect, OpenAI GPT-4o-mini (vision + text)
- RL: Thompson Sampling (multi-armed bandit) with Beta priors, numpy
- CLI: argparse-based with 16 commands

## Key Patterns
- Content engine uses vision analysis → RL scoring → caption generation pipeline
- ETL pipeline auto-refreshes tokens, fetches metrics, trains RL, generates briefs
- Fallback mode: pre-written bypass captions if AI quota exceeded
- Off-brand pages permanently marked via `canva_post_schedule`
- Dashboard reads from PostgreSQL + `data/rl_state.json` + `data/video_watch_matrix.json`

## Original Goal
Grow a TikTok account (luxury mindset, soft life, feminine energy for women 20-40) using data-driven content optimisation. Target: maximise watch time, completion rate, and follower conversion through AI-selected reels and RL-optimised captions.

## Special Notes
- Canva design ID: DAHDMe96N3M (100 Luxury Mindset Reels)
- Canva tokens expire every 4 hours — pipeline auto-refreshes
- RL model persisted at `data/rl_state.json`, trained from `data/video_watch_matrix.json`
- All viewers drop off at second 2 — hook optimisation is critical
- Core audience: 82% female, 25-34, Germany/UK/Poland
- Best performing combo: success theme × reframe_statement hook (reward 0.764)
