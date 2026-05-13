# What's Next — AI TikTok Growth System

> Tied to goal: Grow TikTok account using data-driven RL-optimised content

## Now (immediate next steps — for fresh chat session)

**Second @thetechmudhara post is live (SELF_ONLY) as of 2026-05-13 21:55.** publish_id `v_pub_file~v2-1.7639466974820812803`. Trimmed to 25s starting 10s in (ground-level portrait opener), "stillness isn’t emptiness" overlay 0.2–2.5s, Variant 1 caption.

1. **In ~24h: pull analytics from TikTok Studio for this second post and compare vs first:**
   - First post baseline: 356 views, 7.5% completion, avg watch 3.23s/43s, bounce at 0:01, 0 new followers
   - Goal for this post: completion ≥15%, bounce delayed past 0:03 (the trim + drawtext overlay are the hypothesis being tested — does opening on a face + on-screen text actually fix the 0:01 bounce?)
   - **Note**: post was SELF_ONLY, so FYP distribution = none. Reach numbers will be near-zero; the meaningful signal is the retention curve on the views the creator themselves drives. Decide whether to do a public re-upload (manual, via the TikTok app) once analytics confirm the hook holds.

2. **Lock in the API privacy rule for next post**: unaudited app + Private account is necessary but not sufficient — the `--privacy` flag itself must be `SELF_ONLY`. `PUBLIC_TO_EVERYONE` is rejected with `unaudited_client_can_only_post_to_private_accounts`. Default `post-local` to SELF_ONLY for this profile until the app is audited (or use manual posting in the TikTok app for public reach).

3. **Pre-stage the next clip** (audio strategy from analysis.json: record a voiceover monologue before the next post — voice is the differentiator for the intentional-living niche, generic songs misroute the algorithm).

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
- Second @thetechmudhara post: trim 54s→25s (open on 10s portrait, not aerial), "stillness isn’t emptiness" drawtext overlay 0.2–2.5s, Variant 1 caption, SELF_ONLY publish (PUBLIC_TO_EVERYONE blocked by unaudited-app gate) (2026-05-13)
- Multi-account profile support: `--profile <name>` flag, `new-profile`/`post-local` commands, `thetechmudhara` profile scaffolded (2026-05-13)
- Project files bootstrapped (2026-03-16)
- Reinforcement learning module built and trained (2026-03-19)
- Video watch matrix extracted from 22 screenshots (2026-03-19)
- Content engine integrated with RL scoring (2026-03-19)
- Dashboard updated with RL insights + demographics (2026-03-19)
- Today's RL-optimised caption generated (2026-03-19)
- ffmpeg username overlay on video exports (2026-03-19)
