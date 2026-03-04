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
    DESIGN_ID = "DAHC1GogVkU"  # Copy of 375 Noir Reels

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        if not self.settings.openai_api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in .env")
        self.ai = OpenAI(api_key=self.settings.openai_api_key)
        self.engine = get_engine()

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

        # 3. Pick candidate pages to analyse (sample up to 8 for speed/cost)
        candidates = random.sample(unused, min(8, len(unused)))

        # 4. Fetch ALL pages (paginated) then look up candidate thumbnails
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

        analysed = []
        for page_idx in candidates:
            page = all_pages.get(page_idx)
            if not page:
                continue
            thumb_url = page.get("thumbnail", {}).get("url", "")
            try:
                analysis = self._analyse_thumbnail(thumb_url)
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

    def _analyse_thumbnail(self, thumb_url: str) -> dict:
        """Download thumbnail and ask GPT-4o-mini (vision) to describe theme and suggest a hook."""
        img_bytes = self._fetch_image(thumb_url)
        b64_img = _b64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            "You are a TikTok content strategist. Look at this reel template slide.\n\n"
            "Return ONLY valid JSON with these fields:\n"
            "{\n"
            '  "theme": "one of: luxury, mindset, motivation, softlife, pov, relationship, success, aesthetic, other",\n'
            '  "mood": "e.g. empowering, calm, bold, mysterious, celebratory",\n'
            '  "visible_text": "any text visible on the slide or empty string",\n'
            '  "hook": "suggested opening hook sentence for a TikTok caption, max 12 words",\n'
            '  "rationale": "one sentence why this slide would perform well"\n'
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
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    # ── Caption generation ────────────────────────────────────────────────────

    def _generate_caption(self, analysis: dict, insights: dict) -> tuple[str, str]:
        top_hooks = insights.get("top_hooks", [])
        top_hashtags = insights.get("top_hashtags", [])
        best_themes = insights.get("best_themes", [])

        prompt = (
            "You are a TikTok growth expert for a luxury mindset / soft life account.\n\n"
            f"The reel visual is: theme={analysis.get('theme')}, mood={analysis.get('mood')}, "
            f"hook_idea='{analysis.get('hook')}'\n\n"
            f"Top performing hooks on this account: {top_hooks[:3]}\n"
            f"Best performing themes: {best_themes}\n"
            f"Top performing hashtags: {top_hashtags[:10]}\n\n"
            "Write a TikTok post caption that:\n"
            "- Opens with a punchy hook (1 line)\n"
            "- Has 3-5 lines of body content matching the visual mood\n"
            "- Ends with a question or CTA to drive comments\n"
            "- Is between 150-300 characters total\n"
            "- Feels authentic, not corporate\n\n"
            "Then on a NEW LINE write: HASHTAGS: #tag1 #tag2 ... (8-12 hashtags, mix of niche + broad)\n\n"
            "Use the top performing hashtags from this account but also add relevant trending ones.\n"
            "Return ONLY the caption text followed by the HASHTAGS line. No extra commentary."
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
        """Score each candidate and return the highest scoring one."""
        best_themes = set(insights.get("best_themes", []))
        scores = []
        for page_idx, thumb_url, analysis in analysed:
            score = 0
            theme = analysis.get("theme", "")
            if theme in best_themes:
                score += 3
            if analysis.get("visible_text"):
                score += 1  # slides with text give more to work with
            # Small random tiebreaker for variety
            score += random.random() * 0.5
            scores.append((score, page_idx, thumb_url, analysis))

        scores.sort(reverse=True)
        _, best_idx, best_url, best_analysis = scores[0]
        best_analysis["rationale"] = (
            best_analysis.get("rationale", "") +
            f" Scored {scores[0][0]:.1f} vs {len(scores)} candidates."
        )
        return best_idx, best_url, best_analysis

    # ── Database helpers ──────────────────────────────────────────────────────

    def _get_performance_insights(self) -> dict:
        """Extract what's working from TikTok analytics."""
        with self.engine.begin() as conn:
            # Top performing hooks
            hooks_rows = conn.execute(text("""
                SELECT p.hook_text, SUM(m.views) AS total_views,
                       AVG((m.likes + m.comments + m.shares) * 1.0 / NULLIF(m.views, 0)) AS eng
                FROM posts p
                JOIN post_metrics_daily m ON p.post_id = m.post_id
                WHERE p.hook_text IS NOT NULL
                GROUP BY p.hook_text
                ORDER BY eng DESC NULLS LAST
                LIMIT 5
            """)).fetchall()

            # Top hashtags
            hashtag_rows = conn.execute(text("""
                SELECT p.hashtags FROM posts p
                JOIN post_metrics_daily m ON p.post_id = m.post_id
                WHERE p.hashtags IS NOT NULL
                ORDER BY m.views DESC
                LIMIT 10
            """)).fetchall()

            # Best format types
            format_rows = conn.execute(text("""
                SELECT p.format_type,
                       AVG((m.likes + m.comments + m.shares) * 1.0 / NULLIF(m.views, 0)) AS eng
                FROM posts p
                JOIN post_metrics_daily m ON p.post_id = m.post_id
                WHERE p.format_type IS NOT NULL
                GROUP BY p.format_type
                ORDER BY eng DESC NULLS LAST
            """)).fetchall()

        top_hooks = [r[0] for r in hooks_rows if r[0]]

        all_tags: list[str] = []
        for row in hashtag_rows:
            if row[0]:
                all_tags.extend(
                    t.strip().lstrip("#") for t in row[0].split() if t.startswith("#")
                )
        from collections import Counter
        top_hashtags = [tag for tag, _ in Counter(all_tags).most_common(15)]

        best_themes = [r[0] for r in format_rows if r[0]]

        # Default themes if no data yet
        if not best_themes:
            best_themes = ["luxury", "mindset", "softlife", "motivation", "success"]

        return {
            "top_hooks": top_hooks,
            "top_hashtags": top_hashtags,
            "best_themes": best_themes,
        }

    def _get_unused_pages(self, design_id: str) -> list[int]:
        with self.engine.begin() as conn:
            used = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT page_index FROM canva_post_schedule "
                        "WHERE design_id = :did AND status != 'reset'"
                    ),
                    {"did": design_id},
                ).fetchall()
            }
        # Design has 367 pages (1-indexed)
        all_pages = set(range(1, 368))
        return sorted(all_pages - used)

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
