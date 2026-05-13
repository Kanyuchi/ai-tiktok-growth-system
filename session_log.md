# Session Log — AI TikTok Growth System

## 2026-05-13 21:55 — Second @thetechmudhara post live (trim + overlay + SELF_ONLY publish)

- Trimmed `lv_0_20251108235113~2.mp4` (54s → 25.0s, start at 10s) via `ffmpeg -ss 10 -t 25 -c copy` — kept the ground-level portrait opener instead of the cold drone aerial that bounced viewers at 0:01 on the first post
- Burned text overlay "stillness isn’t emptiness" 0.2–2.5s using `drawtext` at y=h*0.15 (used U+2019 typographic apostrophe to dodge shell-escape on the contraction — cleaner than `\\'` in the documented command)
- Wrote `lv_0_20251108235113_caption.txt` with Variant 1 from the pre-saved analysis ("What does it look like when you finally stop performing busyness?" + intentional-living hashtag set)
- First post attempt with `--privacy PUBLIC_TO_EVERYONE` (as written in whats_next.md) rejected: `unaudited_client_can_only_post_to_private_accounts` (HTTP 403). Reposted with `--privacy SELF_ONLY` → PUBLISH_COMPLETE, publish_id `v_pub_file~v2-1.7639466974820812803`, 8.87 MB single-chunk
- Lesson locked in: even with the account set to Private in TikTok settings, the unaudited app still requires `privacy_level=SELF_ONLY` on the publish call itself. The previous "set account Private" workaround is necessary but not sufficient — the API param must also be SELF_ONLY. Update whats_next.md template accordingly
- Username overlay (`@thetechmudhara`) applied cleanly on top of the drawtext layer (homebrew-ffmpeg drawtext still working post tap-install)

## 2026-05-13 21:48 — Post-mortem on first @thetechmudhara post + niche pivot + next clip pre-analysed

**First post analytics** (lv_0_20250213194144.mp4, 48 MB, posted earlier today): 356 views, 4 likes, 0 comments, 1 share, 0 new followers. Avg watch 3.23s of 43s (7.5% completion). 98.8% from FYP. "Most viewers stopped at 0:01." Audience served: 75% Germany, 6% Austria, 5% Switzerland; 68% male; 25-34 dominant.

**Diagnosis:** algorithm matched DACH male tech/drone audience based on visuals — but the actual audio was a spoken monologue about intentional living vs reactive consumerism. Bounce at 0:01 because opening frame (microscopic figure in vast field) gave zero signal of philosophy content. Niche-content mismatch.

**Pivot:** `data/thetechmudhara/profile.md` niche rewritten from "Tech, AI, Drone, Travel, Fashion" to "Intentional living through the lens of modern life — applied to whatever the canvas is that day." Visuals can vary; perspective stays constant. Caption tone + structure documented in profile.md so `caption-video` writes on-brand automatically.

**Next clip pre-analysed (lv_0_20251108235113~2.mp4, 54s @ 720p):** drone aerial of a rooftop terrace, man in grey sweater (Black, mid-shot at 10s mark). Same failure pattern in opening — no face, no text in first 1s. Frame analysis + 3 caption variants + text-overlay suggestions saved to `exports/thetechmudhara/lv_0_20251108235113~2.analysis.json`. Recommended action: trim to start at 10s for 25s, burn "stillness isn't emptiness" text overlay 0.2-2.5s, post Variant 1 caption ("What does it look like when you finally stop performing busyness?").

**Audio strategy:** original is a generic song. Recommendation = record voiceover monologue (voice = differentiator on this account). User will record before posting OR keep song if not ready.

**Trim + post + analytics check deferred to next session** — whats_next.md has the exact commands ready. User has set @thetechmudhara to Private again (required while app is unaudited).

## 2026-05-13 19:09 — Fix ffmpeg drawtext / username overlay
- Root cause: `homebrew/core` ffmpeg 8.1 ships without libfreetype → no `drawtext` filter → username overlay silently fell back to original video on both profiles
- Fix: swapped to `homebrew-ffmpeg/ffmpeg/ffmpeg` tap (compiles from source, ~60s) — ffmpeg 8.1.1 with libfreetype + libfontconfig + libharfbuzz
- Verified `drawtext` filter present and overlay applies cleanly on a 48 MB drone clip (50 MB → 60 MB after re-encode; still under TikTok's 64 MB single-chunk threshold)
- No code changes — system dep fix only

## 2026-05-13 18:57 — @thetechmudhara live: full OAuth + post pipeline working
- OAuth flow completed for the second account (sandbox app, ngrok HTTPS redirect URI `https://overparticularly-completive-vince.ngrok-free.dev/callback`, sandbox client_key `sbaw6mcvibpjqugtpt`)
- Hit + resolved 4 distinct TikTok policy/protocol gates: localhost redirect URI rejection (switched to ngrok), production vs sandbox client_key mismatch, chunked-upload math (last chunk must be ≥ chunk_size — fixed `_plan_chunks` to use a single chunk for files ≤ 64 MB), unaudited-app restriction (account must be Private for API posts)
- Built `caption-video` CLI command + `video_caption.py`: ffmpeg frame extract (4 frames evenly spaced) → Claude Sonnet 4.6 vision → N JSON-parsed caption variants. Profile-aware (reads niche from `data/<profile>/profile.md`). First test on drone footage generated 3 distinct-angle variants that correctly identified the scene (golden-hour drone shot, two people in a Central European meadow)
- First post: 48 MB drone clip `lv_0_20250213194144.mp4` uploaded SELF_ONLY successfully → PUBLISH_COMPLETE
- Discovered ffmpeg 8.1 (Homebrew default) ships without `drawtext` filter → username overlay silently fails on both profiles. Filed as separate task, posted with `--no-overlay` for now
- Anthropic SDK added to venv (not yet in pyproject.toml dependencies)
- Decisions locked in: while app is unaudited, `@thetechmudhara` must remain Private to use API posting; switching back public means manual posting (with AI captions still useful)

## 2026-05-13 11:34 — Multi-account profile support (new TikTok account scaffolded)
- Added `src/tiktok_ai_analytics/profiles.py` — per-account env files (`.env.<name>`), OAuth session files (`.oauth_session.<name>.json`), `exports/<name>/`, `data/<name>/`
- CLI gained top-level `--profile <name>` flag; activated in `main()` via `load_dotenv(override=True)` before subcommand dispatch
- Token-saving commands (`exchange-code --save`, `refresh-token --save`) now write to the active profile's env file, not always `.env`
- New command `new-profile --name --handle --niche` scaffolds env template + dirs + a profile.md note, and prints OAuth-setup next steps
- New command `post-local --video --caption [--caption-file] [--privacy] [--no-overlay] [--dry-run]` posts a local MP4 directly to TikTok (bypasses Canva/RL — for accounts using external videos)
- `.gitignore` widened to `.env.*` and `.oauth_session.*.json` (previously only the exact filenames were ignored, which would have leaked profile secrets on commit)
- Scaffolded profile `thetechmudhara` (@thetechmudhara, niche: Tech and AI, Drone flying videos, Travel, Fashion). Credentials not yet filled in — pending new TikTok dev-app creation by user
- Docs at `docs/multi-account.md` walking through the full setup
- Analytics/ETL is intentionally still single-account — deferred until the new account is worth tracking

## 2026-03-16 17:27 — Project initialised
- Documentation files created by Claude Code hook

## 2026-03-19 22:15 — ffmpeg username overlay on video exports
- Created `src/tiktok_ai_analytics/video_processor.py` — burns `@thesoftupgrade1` onto MP4s via ffmpeg drawtext filter
- Position: bottom-centre at 82% height, white text with black shadow, Arial 42pt
- Graceful fallback: if ffmpeg missing or fails, original video returned unchanged
- Wired into `cli.py` (post-reel + content-brief --export) and `etl/pipeline.py` (daily pipeline)
- Added `--no-overlay` flag to `post-reel` subparser
- Added `tiktok_username` to Settings dataclass + `.env`

## 2026-03-19 21:30 — Reinforcement learning from video watch matrix
- Analysed 22 TikTok Studio screenshots (5 videos × overview/viewers/engagement tabs)
- Extracted structured watch matrix data to `data/video_watch_matrix.json`
- Built `src/tiktok_ai_analytics/reinforcement.py` — Thompson Sampling multi-armed bandit
  - Arms: theme (9), hook_style (6), mood (8)
  - Composite reward: 20% views + 30% watch_time + 35% completion + 15% followers
  - Learns interaction effects (theme × hook_style combinations)
- Integrated RL into content engine:
  - `_pick_best()` now uses 60% RL score + 30% heuristic + 10% exploration
  - `_generate_caption()` injects RL guidance (best themes, hook styles, retention alert)
  - `_get_performance_insights()` uses RL-ranked themes instead of hardcoded list
- RL auto-trains in daily pipeline before content brief generation
- Added CLI commands: `rl-train`, `rl-status`
- Updated dashboard with 3 new sections:
  - Theme/hook performance charts (RL posterior means)
  - Audience demographics (gender, age, country from watch matrix)
  - Video watch matrix comparison table
- Generated today's RL-optimised caption (success × reframe_statement theme)
- Key findings: success theme (0.764 reward) >> feminine_energy (0.664) >> softlife (0.292) >> motivation (0.184) >> mindset (0.012)
- Updated CLAUDE.md with full project description

## 2026-03-19 21:55 — Exported today's RL-optimised reel
- RL engine selected page #47 (luxury theme, empowering mood, RL-scored 2.74)
- Exported MP4: `exports/DAHDMe96N3M_p47.mp4` (4.6 MB)
- Caption: "You're meant for elegance..." — luxury pillar, question CTA
- Hashtags: #LuxuryLifestyle #SoftLifeEra #HighValueWoman + 7 more
- Marked as 'exported' in canva_post_schedule DB
