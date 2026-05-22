# Recording spec — PoT Matchmaker app walkthrough (for the app-directory Claude)

**Hand this to Claude running in the PoT Matchmaker app repo.** It knows the routes,
selectors, and which screens impress — *it* picks the exact screens. This spec sets the
constraints that make the footage usable for posting back in the growth-system repo.

## Why we're recording
Real-product proof for the launch campaign. The hero film is abstract; people want to see
the app *actually working*. Output target: a **LinkedIn post, 4:5 portrait (primary)** +
a 1:1 square cut, from a builder's-voice account. Short, legible, swipe-stopping.

## Data — read first (decides if it's postable)
- **Strongly prefer demo / seeded data** (placeholder names like the "Mira Chen / Karim Idrissi"
  fixtures). If you record against demo data, **there is nothing to blur** and it ships immediately.
- Only if no demo data exists, record the real account — then names/faces get blurred back here
  (fiddly, never perfect). Avoid this if you can.
- Never show: real emails, magic-link URLs/tokens, settings/admin, other users' private fields.

## The story to capture (you choose the exact screens)
Aim for ~4–6 beats, each a few seconds, that tell: *"it reads the room and hands you the 5 that matter."*
1. **Entry** — the "before you land" moment (dashboard / matches landing).
2. **My Matches** — the ranked list. The hero screen. Let it breathe.
3. **Why this meeting matters** — open one match; linger on the reason line. *This is the differentiator —
   no other tool says why.* Most important beat.
4. **AI Concierge** (if it exists) — ask one real, specific question ("who should I meet about
   stablecoin licensing?") and show it answer. Very strong if available.
5. **Mutual match** — the opt-in / "yes before the handshake" moment.
6. (Optional) the one-link-in / inbox moment — only if no real email/token shows.

## Technical constraints (so it crops clean for 4:5)
- **Viewport:** try **1080×1350 (4:5)** first — if the app is responsive and lays out well, record
  at that aspect and we need *zero* cropping. If the layout breaks at portrait, fall back to
  **1600×1000 or 1920×1080 landscape** and **keep the key UI (cards, the "why" line) centred** so a
  centre-crop to 4:5 keeps it. (Processing here auto-crops either way.)
- **Zoom:** bump browser zoom to ~110–125% so text is large and readable in-feed.
- **Pacing:** deliberate. Pause ~1.5–2s on each key screen. Scroll slowly. No frantic clicking.
  Move the cursor smoothly to what matters. Total raw 30–90s is plenty — we trim.
- **Format:** Playwright `recordVideo` → `.webm` is perfect (we convert). Or export `.mp4`.
- **No audio needed** (we strip it).

## Turnkey Playwright snippet (adapt selectors/route)
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)          # watch it run
    ctx = browser.new_context(
        viewport={"width": 1080, "height": 1350},        # 4:5; or 1600x1000 landscape
        record_video_dir="recordings/",
        record_video_size={"width": 1080, "height": 1350},
        device_scale_factor=2,                            # crisp text
    )
    page = ctx.new_page()
    page.goto("https://meet.proofoftalk.io/...")          # authenticated route / after magic-link
    # --- your scripted tour with deliberate waits ---
    page.wait_for_timeout(2000)
    # page.click(...); page.wait_for_timeout(2000); page.mouse.wheel(0, 400); ...
    ctx.close()                                           # <-- video is finalized on context close
    browser.close()
# video lands in recordings/<hash>.webm
```

## Handoff back to the growth-system repo
1. Record → you get `recordings/<hash>.webm`.
2. Move/copy it to: **`AI TikTok Growth System/matchmaker_content/raw/`** (create the folder).
3. Tell me the filename + which data type (demo / real). Then here I run:
   ```
   scripts/process_recording.sh matchmaker_content/raw/<file>.webm matchmaker_walkthrough
   ```
   → produces `_4x5.mp4` (1080×1350) + `_1x1.mp4` in `matchmaker_content/assets/`, ready for caption + post.
4. If real data: also note which screens showed names so I can blur before cropping.
