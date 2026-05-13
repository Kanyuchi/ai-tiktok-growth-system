# What's Next — AI TikTok Growth System

> Tied to goal: Grow TikTok account using data-driven RL-optimised content

## Now (immediate next steps — for fresh chat session)

**Pick up: trim + post lv_0_20251108235113~2.mp4 for @thetechmudhara.** Account is set to Private on TikTok (required while the dev app is unaudited). All artefacts saved.

1. **Trim** `exports/thetechmudhara/lv_0_20251108235113~2.mp4` (54s → 25s, start at 10s):
   ```bash
   ffmpeg -i "exports/thetechmudhara/lv_0_20251108235113~2.mp4" \
     -ss 10 -t 25 -c copy \
     "exports/thetechmudhara/lv_0_20251108235113_trimmed.mp4"
   ```
2. **Add text overlay** "stillness isn't emptiness" in first 0–2s. ffmpeg now has drawtext (fixed in previous session). Suggested command:
   ```bash
   ffmpeg -i exports/thetechmudhara/lv_0_20251108235113_trimmed.mp4 \
     -vf "drawtext=text='stillness isn\\'t emptiness':fontsize=64:fontcolor=white@0.95:shadowcolor=black@0.6:shadowx=3:shadowy=3:x=(w-text_w)/2:y=h*0.15:enable='between(t,0.2,2.5)'" \
     -codec:a copy exports/thetechmudhara/lv_0_20251108235113_final.mp4
   ```
3. **Post** via API:
   ```bash
   python scripts/tiktok_cli.py --profile thetechmudhara post-local \
     --video exports/thetechmudhara/lv_0_20251108235113_final.mp4 \
     --caption-file exports/thetechmudhara/lv_0_20251108235113_caption.txt \
     --privacy PUBLIC_TO_EVERYONE
   ```
4. **Caption to write to `lv_0_20251108235113_caption.txt`** (Variant 1, already generated, in `lv_0_20251108235113~2.analysis.json`):
   > What does it look like when you finally stop performing busyness?
   >
   > Stood on that terrace and realised — I wasn't resting. I was just waiting to be productive again. There's a difference between pausing and actually being still. One is recovery. The other is presence. Most of us only practise the first one.
   >
   > #intentionalliving #mindsetshift #soulwork #slowliving #dronephotography #droneview #intentionallife #beingpresent #consciousliving #thetechmudhara

5. **After posting**: wait 24h, check analytics in TikTok Studio. Compare retention/completion vs first post (which had 7.5% completion + 0:01 bounce). Goal: completion ≥15%, bounce delayed past 0:03.

## Soon
- Decide whether `@thetechmudhara` is worth tracking analytically — if yes, scope DB schema by account (add `account_open_id` column) so `run-daily` and the dashboard can be profile-aware
- Record real voiceover monologues for future @thetechmudhara posts (Claude's analysis: voice = the differentiator vs generic songs/trending sounds)
- Automate screenshot → watch matrix extraction (OCR or TikTok API v2)
- Add mood arm training (currently no mood data from screenshots)
- A/B test: RL-selected vs random content to measure lift
- Add retention curve analysis (per-second drop-off, not just "stopped at 0:02")
- Implement UCB (Upper Confidence Bound) as alternative to Thompson Sampling

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
