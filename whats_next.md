# What's Next — AI TikTok Growth System

> Tied to goal: Grow TikTok account using data-driven RL-optimised content

## Now (immediate next steps)
1. Post today's RL-optimised reel (caption in `exports/rl_post_2026-03-19.txt`)
2. Add more videos to watch matrix as new analytics come in (feed RL model)
3. Run `rl-train` after each batch of new screenshots to update posteriors
4. Test dashboard with `streamlit run dashboard/app.py` — verify new RL sections render
5. Track whether success × reframe_statement actually outperforms in next 7 days

## Soon
- Automate screenshot → watch matrix extraction (OCR or TikTok API v2)
- Add mood arm training (currently no mood data from screenshots)
- A/B test: RL-selected vs random content to measure lift
- Add retention curve analysis (per-second drop-off, not just "stopped at 0:02")
- Implement UCB (Upper Confidence Bound) as alternative to Thompson Sampling

## Later / Backlog
- Multi-objective RL: separate bandits for reach vs retention vs conversion
- Contextual bandits: use time-of-day, day-of-week as context features
- Audience segmentation: different content for DE/UK/PL markets
- Auto-post pipeline: full daily_pipeline → rl_train → brief → export → post without manual steps

## Done ✓
- Project files bootstrapped (2026-03-16)
- Reinforcement learning module built and trained (2026-03-19)
- Video watch matrix extracted from 22 screenshots (2026-03-19)
- Content engine integrated with RL scoring (2026-03-19)
- Dashboard updated with RL insights + demographics (2026-03-19)
- Today's RL-optimised caption generated (2026-03-19)
- ffmpeg username overlay on video exports (2026-03-19)
