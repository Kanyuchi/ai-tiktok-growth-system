from __future__ import annotations

"""
Content Brief Engine
====================
1. Fetches page thumbnails from the Canva design (375 Noir Reels)
2. Uses Google Gemini Flash (vision) to read the theme/mood of each slide
3. Cross-references with TikTok performance data from PostgreSQL
4. Picks the best unused slide for today
5. Generates an optimised caption + hashtags

All analysis results are cached in canva_post_schedule to avoid re-scanning.
"""

import json
import random
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import base64 as _b64
from openai import OpenAI
from sqlalchemy import text

from .config import Settings, load_settings
from .db import get_engine


@dataclass
class ContentBrief:
    page_index: int
    thumbnail_url: str
    theme: str
    mood: str
    hook_suggestion: str
    caption: str
    hashtags: str
    rationale: str


class ContentEngine:
    DESIGN_ID = "DAHDMe96N3M"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        if not self.settings.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in .env")
        self.ai = OpenAI(api_key=self.settings.openai_api_key)
        self.engine = get_engine()

        # Load RL model (graceful fallback if not trained yet)
        from .reinforcement import ContentRL
        self.rl = ContentRL.load()

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_daily_brief(self, design_id: str | None = None) -> ContentBrief:
        """Pick today's best reel and generate caption + hashtags."""
        design_id = design_id or self.DESIGN_ID

        # 1. Get performance insights from TikTok data
        insights = self._get_performance_insights()

        # 2. Get list of all pages we haven't used yet
        unused = self._get_unused_pages(design_id)
        if not unused:
            print("[ENGINE] All pages used — resetting schedule.")
            self._reset_schedule(design_id)
            unused = self._get_unused_pages(design_id)

        # 3. Fetch ALL available pages (paginated) from Canva
        from .canva_client import CanvaClient
        canva = CanvaClient(
            access_token=self.settings.canva_access_token,
            settings=self.settings,
        )
        all_pages: dict[int, dict] = {}
        continuation = None
        while True:
            params: dict = {"limit": 50}
            if continuation:
                params["continuation"] = continuation
            pages_data = canva._request("GET", f"/designs/{design_id}/pages", params=params)
            for p in pages_data.get("items", []):
                all_pages[p["index"]] = p
            continuation = pages_data.get("continuation")
            if not continuation:
                break

        print(f"[ENGINE] Canva returned {len(all_pages)} pages.")

        # Intersect unused DB list with pages actually available from Canva API
        available_unused = sorted(set(unused) & set(all_pages.keys()))
        if not available_unused:
            print("[ENGINE] No unused pages available from Canva — resetting schedule.")
            self._reset_schedule(design_id)
            available_unused = sorted(all_pages.keys())

        # 4. Pick candidate pages to analyse (sample up to 8 for speed/cost)
        candidates = random.sample(available_unused, min(8, len(available_unused)))

        analysed = []
        for page_idx in candidates:
            page = all_pages.get(page_idx)
            if not page:
                continue
            thumb_url = page.get("thumbnail", {}).get("url", "")
            try:
                analysis = self._analyse_thumbnail(thumb_url)
                if analysis.get("skip"):
                    reason = analysis.get("skip_reason", "off-brand")
                    print(f"[ENGINE] Skipping page {page_idx} (off-brand): {reason}")
                    # Mark in DB so it's never picked again
                    self._mark_offbrand(design_id, page_idx)
                    continue
                analysed.append((page_idx, thumb_url, analysis))
            except Exception as e:
                print(f"[ENGINE] Skipping page {page_idx}: {e}")

        if not analysed:
            raise RuntimeError("Could not analyse any candidate pages.")

        # 5. Pick the best page based on performance insights + analysis
        best_page_idx, best_thumb_url, best_analysis = self._pick_best(analysed, insights)

        # 6. Generate full caption + hashtags
        caption, hashtags = self._generate_caption(best_analysis, insights)

        # 7. Save to schedule
        self._mark_scheduled(design_id, best_page_idx, best_thumb_url, caption, hashtags)

        return ContentBrief(
            page_index=best_page_idx,
            thumbnail_url=best_thumb_url,
            theme=best_analysis.get("theme", ""),
            mood=best_analysis.get("mood", ""),
            hook_suggestion=best_analysis.get("hook", ""),
            caption=caption,
            hashtags=hashtags,
            rationale=best_analysis.get("rationale", ""),
        )

    def list_schedule(self) -> list[dict]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT * FROM canva_post_schedule ORDER BY id DESC LIMIT 30")
            ).fetchall()
        return [dict(r._mapping) for r in rows]

    # ── Gemini vision analysis ────────────────────────────────────────────────

    # Account SOP — embedded into every prompt so the AI never generalises
    ACCOUNT_SOP = (
        "ACCOUNT IDENTITY:\n"
        "This is a TikTok account for women focused on luxury mindset, soft life, and personal elevation. "
        "The content is aspirational, feminine, and empowering. Every post should feel like it was written "
        "by a woman who has already become her best self and is speaking directly to women on that journey.\n\n"
        "CONTENT PILLARS (stick to these only):\n"
        "1. Soft life — peace, ease, abundance, rejecting stress and struggle\n"
        "2. Luxury mindset — wealth consciousness, elevating standards, self-worth\n"
        "3. Personal growth — becoming her, identity shifts, levelling up quietly\n"
        "4. Feminine energy — boundaries, self-love, knowing your worth\n"
        "5. Motivation — short punchy truths, not generic quotes\n\n"
        "WHAT THIS ACCOUNT NEVER POSTS:\n"
        "- Giveaways, competitions, or win/follow/share prompts\n"
        "- Promotional or product advertising content\n"
        "- Generic hustle culture or grind content\n"
        "- Anything that sounds corporate, salesy, or templated\n"
        "- Long paragraphs — always short punchy lines\n\n"
        "TONE: Authentic. Feminine. Aspirational. Direct. Never corporate.\n"
        "AUDIENCE: Women aged 20-40 who want to elevate their lifestyle, mindset, and self-worth.\n"
    )

    def _analyse_thumbnail(self, thumb_url: str) -> dict:
        """Download thumbnail and ask GPT-4o-mini (vision) to describe theme and suggest a hook.
        Returns dict with skip=True if the slide is off-brand (giveaway, promo, ad)."""
        img_bytes = self._fetch_image(thumb_url)
        b64_img = _b64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            f"{self.ACCOUNT_SOP}\n"
            "Look at this reel template slide and assess whether it fits this account.\n\n"
            "Return ONLY valid JSON with these fields:\n"
            "{\n"
            '  "skip": true/false — true if this slide is a giveaway, competition, promo, ad, product sale, '
            'follow/share/tag prompt, or anything off-brand for this account. false if it fits the content pillars.,\n'
            '  "skip_reason": "why it was skipped, or empty string if not skipped",\n'
            '  "theme": "one of: luxury, mindset, motivation, softlife, pov, relationship, success, aesthetic",\n'
            '  "mood": "e.g. empowering, calm, bold, mysterious, serene",\n'
            '  "visible_text": "any text visible on the slide or empty string",\n'
            '  "hook": "suggested opening hook sentence matching the account tone, max 12 words",\n'
            '  "rationale": "one sentence why this slide fits or does not fit the account"\n'
            "}"
        )

        response = self.ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}", "detail": "low"}},
                ],
            }],
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    # ── Caption generation ────────────────────────────────────────────────────

    def _generate_caption(self, analysis: dict, insights: dict) -> tuple[str, str]:
        top_hooks = insights.get("top_hooks", [])
        top_hashtags = insights.get("top_hashtags", [])
        best_themes = insights.get("best_themes", [])

        best_posts = insights.get("best_posts", [])
        avg_watch = insights.get("avg_watch_benchmark", 0)
        avg_comp = insights.get("avg_completion_benchmark", 0)

        best_posts_text = "\n".join(
            f'  - "{p["caption_start"]}" → {p["avg_watch_s"]}s watch, {p["completion_pct"]}% watched full'
            for p in best_posts
        ) or "  (no data yet)"

        # Inject RL-learned guidance
        rl_guidance = self.rl.get_caption_guidance()

        prompt = (
            f"{self.ACCOUNT_SOP}\n"
            "──────────────────────────────────────\n"
            "Write a TikTok caption for this reel.\n\n"
            f"VISUAL: theme={analysis.get('theme')}, mood={analysis.get('mood')}\n"
            f"Text on slide: '{analysis.get('visible_text', '')}'\n"
            f"Suggested hook from visual: '{analysis.get('hook')}'\n\n"
            f"{rl_guidance}\n\n"
            f"ACCOUNT PERFORMANCE DATA:\n"
            f"- Avg watch time: {avg_watch}s | Avg completion: {avg_comp}%\n"
            f"- Every video drops off at 0:01-0:02 — Line 1 MUST stop the scroll\n"
            f"- Top performing posts (model your style on these):\n{best_posts_text}\n\n"
            f"Top performing hooks: {top_hooks[:3]}\n"
            f"Top performing hashtags: {top_hashtags[:10]}\n\n"
            "CAPTION STRUCTURE:\n"
            "- Line 1: Scroll-stopping hook — identity, truth, or curiosity. Max 10 words.\n"
            "- Lines 2-4: Short punchy lines (1 idea per line). Match the visual mood.\n"
            "- Final line: Question or CTA that invites comments.\n"
            "- Total: 150-250 characters. No long paragraphs.\n"
            "- Must fit one of the 5 content pillars above. No giveaways, no promos.\n\n"
            "Then on a NEW LINE write: HASHTAGS: #tag1 #tag2 ... (8-12 hashtags)\n"
            "Return ONLY the caption followed by the HASHTAGS line. No commentary."
        )

        response = self.ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        raw = response.choices[0].message.content.strip()

        if "HASHTAGS:" in raw:
            parts = raw.split("HASHTAGS:", 1)
            caption = parts[0].strip()
            hashtags = "HASHTAGS: " + parts[1].strip()
        else:
            caption = raw
            hashtags = " ".join(f"#{t}" for t in top_hashtags[:10])

        return caption, hashtags

    # ── Selection logic ───────────────────────────────────────────────────────

    def _pick_best(
        self, analysed: list[tuple[int, str, dict]], insights: dict
    ) -> tuple[int, str, dict]:
        """Score each candidate using RL-informed weights + heuristics."""
        best_themes = set(insights.get("best_themes", []))
        rl_weights = self.rl.get_scoring_weights()
        scores = []
        for page_idx, thumb_url, analysis in analysed:
            theme = analysis.get("theme", "")
            mood = analysis.get("mood", "")

            # RL score (0-1 range, scaled to 0-5)
            rl_score = self.rl.score_candidate(theme=theme, mood=mood) * 5

            # Heuristic bonuses
            heuristic = 0
            if theme in best_themes:
                heuristic += 2
            if analysis.get("visible_text"):
                heuristic += 1

            # Combined: 60% RL, 30% heuristic, 10% exploration noise
            score = rl_score * 0.6 + heuristic * 0.3 + random.random() * 0.5
            scores.append((score, page_idx, thumb_url, analysis))

        scores.sort(reverse=True)
        _, best_idx, best_url, best_analysis = scores[0]
        best_analysis["rationale"] = (
            best_analysis.get("rationale", "") +
            f" RL-scored {scores[0][0]:.2f} vs {len(scores)} candidates."
        )
        return best_idx, best_url, best_analysis

    # ── Database helpers ──────────────────────────────────────────────────────

    def _get_performance_insights(self) -> dict:
        """Extract what's working from TikTok analytics."""
        with self.engine.begin() as conn:
            # Top posts by composite score: completion_rate * 0.5 + engagement * 0.3 + watch_time * 0.2
            top_posts_rows = conn.execute(text("""
                SELECT p.caption, p.hook_text,
                       AVG(m.avg_watch_time_seconds) AS avg_watch,
                       AVG(m.completion_rate) AS avg_completion,
                       AVG((m.likes + m.comments + m.shares) * 1.0 / NULLIF(m.views, 0)) AS eng,
                       AVG(m.completion_rate) * 0.5
                           + AVG((m.likes + m.comments + m.shares) * 1.0 / NULLIF(m.views, 0)) * 0.3
                           + (AVG(m.avg_watch_time_seconds) / 10.0) * 0.2 AS score
                FROM posts p
                JOIN post_metrics_daily m ON p.post_id = m.post_id
                WHERE m.avg_watch_time_seconds IS NOT NULL
                GROUP BY p.caption, p.hook_text
                ORDER BY score DESC NULLS LAST
                LIMIT 5
            """)).fetchall()

            # Top hashtags from best-performing posts (by completion rate)
            hashtag_rows = conn.execute(text("""
                SELECT p.hashtags, AVG(m.completion_rate) AS avg_comp
                FROM posts p
                JOIN post_metrics_daily m ON p.post_id = m.post_id
                WHERE p.hashtags IS NOT NULL AND m.completion_rate IS NOT NULL
                GROUP BY p.hashtags
                ORDER BY avg_comp DESC NULLS LAST
                LIMIT 10
            """)).fetchall()

            # Avg watch time benchmark
            bench = conn.execute(text("""
                SELECT AVG(m.avg_watch_time_seconds) AS avg_watch,
                       AVG(m.completion_rate) AS avg_comp
                FROM post_metrics_daily m
                WHERE m.avg_watch_time_seconds IS NOT NULL
            """)).fetchone()

        top_hooks = [r.hook_text for r in top_posts_rows if r.hook_text]
        # Fall back to caption first words if hook_text not set
        if not top_hooks:
            top_hooks = [(r.caption or "")[:60] for r in top_posts_rows if r.caption]

        all_tags: list[str] = []
        for row in hashtag_rows:
            if row[0]:
                all_tags.extend(
                    t.strip().lstrip("#") for t in row[0].split() if t.startswith("#")
                )
        from collections import Counter
        top_hashtags = [tag for tag, _ in Counter(all_tags).most_common(15)]

        # Best performers info for caption prompt
        best_posts_summary = []
        for r in top_posts_rows[:3]:
            best_posts_summary.append({
                "caption_start": (r.caption or "")[:80],
                "avg_watch_s": round(r.avg_watch or 0, 2),
                "completion_pct": round((r.avg_completion or 0) * 100, 1),
                "score": round(r.score or 0, 3),
            })

        avg_watch_benchmark = round(bench.avg_watch or 0, 2) if bench else 0
        avg_completion_benchmark = round((bench.avg_comp or 0) * 100, 1) if bench else 0

        # Use RL-ranked themes instead of hardcoded list
        rl_rankings = self.rl.get_feature_rankings()
        best_themes = [t[0] for t in rl_rankings["themes"][:5]] or [
            "success", "feminine_energy", "mindset", "motivation", "softlife"
        ]

        return {
            "top_hooks": top_hooks,
            "top_hashtags": top_hashtags,
            "best_themes": best_themes,
            "best_posts": best_posts_summary,
            "avg_watch_benchmark": avg_watch_benchmark,
            "avg_completion_benchmark": avg_completion_benchmark,
        }

    def _get_unused_pages(self, design_id: str) -> list[int]:
        with self.engine.begin() as conn:
            used = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT page_index FROM canva_post_schedule "
                        "WHERE design_id = :did AND status NOT IN ('reset', 'offbrand')"
                    ),
                    {"did": design_id},
                ).fetchall()
            }
        all_pages = set(range(1, 401))
        return sorted(all_pages - used)

    def _mark_offbrand(self, design_id: str, page_index: int) -> None:
        """Permanently mark a page as off-brand so it is never picked again."""
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO canva_post_schedule
                      (design_id, page_index, scheduled_date, caption, hashtags, thumbnail_url, status)
                    VALUES (:did, :idx, CURRENT_DATE, '', '', '', 'offbrand')
                    ON CONFLICT (design_id, page_index) DO UPDATE SET status = 'offbrand'
                """),
                {"did": design_id, "idx": page_index},
            )
        print(f"[ENGINE] Page {page_index} marked as off-brand permanently.")

    def _reset_schedule(self, design_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE canva_post_schedule SET status = 'reset' WHERE design_id = :did"),
                {"did": design_id},
            )

    def _mark_scheduled(
        self,
        design_id: str,
        page_index: int,
        thumbnail_url: str,
        caption: str,
        hashtags: str,
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO canva_post_schedule
                      (design_id, page_index, scheduled_date, caption, hashtags, thumbnail_url, status)
                    VALUES
                      (:did, :idx, :sdate, :caption, :hashtags, :thumb, 'scheduled')
                    ON CONFLICT (design_id, page_index) DO UPDATE SET
                      scheduled_date = EXCLUDED.scheduled_date,
                      caption = EXCLUDED.caption,
                      hashtags = EXCLUDED.hashtags,
                      status = 'scheduled'
                """),
                {
                    "did": design_id,
                    "idx": page_index,
                    "sdate": date.today(),
                    "caption": caption,
                    "hashtags": hashtags,
                    "thumb": thumbnail_url,
                },
            )

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch_image(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
