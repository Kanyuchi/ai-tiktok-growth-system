# What's Next — AI TikTok Growth System

> Tied to goal: Grow TikTok account using data-driven RL-optimised content

## Now (immediate next steps)
1. **New account `@thetechmudhara`**: create the TikTok dev app (https://developers.tiktok.com/apps), add `video.publish` scope, paste client_id/secret into `.env.thetechmudhara`
2. **OAuth `@thetechmudhara`**: `python scripts/tiktok_cli.py --profile thetechmudhara auth-url` → authorise → `exchange-code --code <c> --save`
3. **Drop the new account's MP4s into `exports/thetechmudhara/`** and post with `--profile thetechmudhara post-local`
4. Post today's RL-optimised reel for the luxury account (caption in `exports/rl_post_2026-03-19.txt`)
5. Add more videos to watch matrix as new analytics come in (feed RL model)

## Soon
- Decide whether `@thetechmudhara` is worth tracking analytically — if yes, scope DB schema by account (add `account_open_id` column) so `run-daily` and the dashboard can be profile-aware
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
- Multi-account profile support: `--profile <name>` flag, `new-profile`/`post-local` commands, `thetechmudhara` profile scaffolded (2026-05-13)
- Project files bootstrapped (2026-03-16)
- Reinforcement learning module built and trained (2026-03-19)
- Video watch matrix extracted from 22 screenshots (2026-03-19)
- Content engine integrated with RL scoring (2026-03-19)
- Dashboard updated with RL insights + demographics (2026-03-19)
- Today's RL-optimised caption generated (2026-03-19)
- ffmpeg username overlay on video exports (2026-03-19)
