# Proof of Talk Matchmaker — Launch Campaign Plan

**Date:** 2026-05-20
**Owner:** Shaun (with Zohair, Karl, Ferd)
**Status:** Approved — building
**Event:** Proof of Talk 2026 · Louvre Palace, Paris · June 2–3, 2026
**Anchor asset:** `matchmaker_content/Updated Matchmaker Video .mp4` (65s · 4K · 16:9)
**Channels:** LinkedIn (primary) + X. (IG / 9:16 out of scope for now.)
**Workflow:** draft-mode now → automated approval-queue pipeline after the launch proves voice quality.

---

## 1. Arc (Approach A — Big-Bang + Tail)

Two warm-ups → one concentrated launch moment (**Tue May 26, T-7**) → daily-ish countdown tail → live event coverage → wrap. Voice is borrowed from the film's own lines, not invented.

Today = Wed May 20 = **T-13**. Event Day 1 = Tue June 2.

## 2. Content pillars

Every post traces to exactly one pillar.

| # | Pillar | Hook bank (from the film) |
|---|---|---|
| **P1** | The reframe — quality > volume networking | "You stop working the room. The room was worked for you." · "Find your 5, not your 500." |
| **P2** | Product proof — the actual matcher | "Reads every attendee… tells you exactly why." · Complementary · Non-Obvious · Deal-Ready · "The yes happens before the handshake." |
| **P3** | Who's in the room — social proof / FOMO | "$18T in the room." · "Your matches are already in the room." · named speakers + sponsors |
| **P4** | Build story — founder POV | "We built this because every conference hands you a CSV and calls it networking." |
| **P5** | Activation / urgency | "Before you even land." · "Claim your ticket." · "Check your inbox." · countdown |

## 3. Voices → pillars

| Voice | Owns | Tone |
|---|---|---|
| **Zohair** (founder) | P1, P4 | Reflective, conviction, "I built this" |
| **Karl** (ops/numbers) | P2, P3 | Proof, metrics, "436 profiles read, N matches" |
| **Ferd** (community) | P3, P5 | Warm, "check your inbox", invites |
| **Shaun** (you) | amplify all + replies | Builder's-eye, behind-the-scenes |
| **PoT company page** | the anchor posts | Brand, premium |

## 4. Calendar

| Date | T- | Pillar | Channel / who | Asset |
|---|---|---|---|---|
| Thu May 21 | T-12 | P4 warm-up — founder problem post | LI: Zohair | `posts/warmup-2026-05-21-zohair.md` |
| Mon May 25 | T-8 | P2/P5 tease — "tomorrow" + 1 product frame | LI + X: company | `posts/tease-2026-05-25.md` |
| **Tue May 26** | **T-7** | **LAUNCH — full film** | LI company → repost stack + X video & thread | `posts/launch-2026-05-26.md` |
| Wed May 27 | T-6 | P2 — how the matching works | LI: Karl · X | `posts/countdown-2026-05-27.md` |
| Thu May 28 | T-5 | P3 — who's in the room (sector spotlight) | LI: Ferd · X | `posts/countdown-2026-05-28.md` |
| Fri May 29 | T-4 | P1 — "stop working the room" + clip | X (light) | `posts/countdown-2026-05-29.md` |
| Sat–Sun May 30–31 | T-3/2 | rest / 1 optional evergreen reshare | — | — |
| Mon Jun 1 | T-1 | P5 last-call — "doors at the Louvre tomorrow" | LI + X: company + all | `posts/countdown-2026-06-01.md` |
| Tue–Wed Jun 2–3 | Event | live — mutual-match moments, quotes, on-the-ground | LI + X: Shaun + company | `posts/event-live.md` |
| Thu Jun 4+ | Post | wrap + metrics + post-mortem | LI: company + repo | `posts/wrap.md` |

### Launch-day timing (Tue May 26, Paris time)
- **09:00** — PoT company page post + native video.
- **09:30 / 10:00 / 10:30** — Zohair / Karl / Ferd reposts cascade (30 min apart).
- **~10:45** — Shaun repost.
- **+1h** — Karl + Ferd first-comment: "DM me your ticket email for your magic link early."
- **+24h** — performance check; decide on paid boost (brief threshold: 10k impressions + 3% CTR in 72h → $500–1k).

## 5. Tracking
All clickable links use `?utm_source=linkedin&utm_campaign=launch_video_2026` (swap `linkedin`→`x` on X). Tickets → `proofoftalk.io`; product → `meet.proofoftalk.io`.

## 6. Community-reply pipeline (draft + approve)

**Loop:** scheduled supervised Playwright session (you logged in) → reads the team's new posts + commenters + a "Proof of Talk Matchmaker" search → I draft one reply per item into an **approval queue** (`replies/queue-YYYY-MM-DD.md`) → you tap approve → it posts. Both platforms human-gated.

| Comment type | Response pattern |
|---|---|
| "How does it work?" | 1-line explainer + link to meet.proofoftalk.io |
| "I'm coming!" | warm + "check your inbox for your matches" |
| Skeptic ("just another conf app") | the reframe, no defensiveness |
| VC/founder self-promo | bridge: "you'd get matched with exactly that kind of person" |
| Press / partner | route to Shaun/Zohair, do not auto-engage |

### Draft → pipeline upgrade gate
Stay manual (you forward, I draft) through the **May-26 launch**. Flip on the scheduled pipeline only after **~10 drafted replies approved with minor edits** — proof the voice is right. Until then, no automation touches live accounts.

## 7. Success metrics (from launch-video brief)

| Metric | Target |
|---|---|
| LinkedIn impressions (72h, all posts) | 25k |
| LinkedIn CTR to proofoftalk.io | 3% |
| Magic-link claims (of 436 ticket-holders) | 60% within 7d |
| New tickets attributable to campaign | 40 |
| "DM me your email" replies | 30 |

## 8. Where things live
- This plan + drafts: `matchmaker_content/`
- Post copy: `matchmaker_content/posts/`
- Reply queues: `matchmaker_content/replies/`
- Crops / graphics / clips: `matchmaker_content/assets/`
- Video frames (reference): `matchmaker_content/frames/`

## 9. Dependencies / risks (not in my control)
- Zohair sign-off on final film + go date.
- Reposters (Zohair/Karl/Ferd) briefed before T-day.
- Magic-link / email path working for the 436 (per project_state: email verified working 2026-05-20, transactional-only per Zohair).
- A 1:1 or 4:5 LinkedIn crop of the film would gain feed real estate (optional; 16:9 posts fine).
