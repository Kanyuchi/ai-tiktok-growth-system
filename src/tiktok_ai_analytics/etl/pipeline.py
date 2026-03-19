from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from ..auth import TikTokAuthClient
from ..canva_auth import CanvaAuthClient
from ..config import load_settings
from ..db import get_engine
from ..env_store import upsert_env_values
from ..kpis import comment_rate, engagement_rate, retention_proxy, share_rate
from .tiktok_client import FetchedMetrics, FetchedPost, TikTokClient


def run_daily_pipeline(max_videos: int | None = None, persist_tokens: bool = True) -> None:
    settings = load_settings()
    access_token = settings.tiktok_access_token
    refresh_token = settings.tiktok_refresh_token

    if settings.tiktok_auto_refresh_on_run and refresh_token:
        refreshed = TikTokAuthClient(settings).refresh_access_token(refresh_token=refresh_token)
        access_token = refreshed.access_token
        refresh_token = refreshed.refresh_token

        if persist_tokens:
            upsert_env_values(
                {
                    "TIKTOK_ACCESS_TOKEN": access_token,
                    "TIKTOK_REFRESH_TOKEN": refresh_token,
                }
            )
            print("[AUTH] Refreshed tokens and updated .env")

    # Auto-refresh Canva token (expires every 4h — always refresh before pipeline)
    if settings.canva_refresh_token and persist_tokens:
        try:
            canva_refreshed = CanvaAuthClient(settings).refresh_access_token(settings.canva_refresh_token)
            upsert_env_values({
                "CANVA_ACCESS_TOKEN": canva_refreshed.access_token,
                "CANVA_REFRESH_TOKEN": canva_refreshed.refresh_token,
            })
            print("[AUTH] Canva token refreshed and updated .env")
        except Exception as e:
            print(f"[AUTH] Canva token refresh failed (continuing): {e}")

    if not access_token:
        raise RuntimeError(
            "Missing TikTok access token. Generate auth URL via `python -m tiktok_ai_analytics.cli auth-url`."
        )

    client = TikTokClient(access_token=access_token, settings=settings)
    posts, metrics = client.fetch_posts_and_metrics(max_videos=max_videos)

    if not posts:
        print("[PIPELINE] No videos returned from TikTok API.")
        return

    snapshot_date = _today_in_timezone(settings.timezone)

    engine = get_engine()
    with engine.begin() as conn:
        for post, metric in zip(posts, metrics, strict=True):
            _upsert_post(conn, post)
            _upsert_metric(conn, metric, snapshot_date)
            _log_kpis(post, metric)

    print(f"[PIPELINE] Upserted {len(posts)} posts for {snapshot_date}")

    # Re-train RL model if watch matrix exists (fast — runs in <1s)
    from ..reinforcement import ContentRL, WATCH_MATRIX_PATH
    if WATCH_MATRIX_PATH.exists():
        try:
            rl = ContentRL.load()
            rl.learn_from_watch_matrix()
            rl.save()
            print("[RL] Model updated from watch matrix.")
        except Exception as e:
            print(f"[RL] Update failed (continuing): {e}")

    # Generate daily content brief + export MP4 (bypass OpenAI if quota exceeded)
    _run_content_brief(settings)

    print("[PIPELINE] Daily pipeline completed.")


def _run_content_brief(settings) -> None:
    """Generate today's content brief and export the reel MP4."""
    import random
    from datetime import date
    from pathlib import Path

    from sqlalchemy import text as sa_text

    from ..canva_client import CanvaClient
    from ..content_engine import ContentEngine
    from ..db import get_engine

    DESIGN_ID = ContentEngine.DESIGN_ID

    BYPASS_CAPTIONS = [
        (
            "She's not waiting for permission. She already decided. 👑\n\n"
            "The soft life isn't luck — it's a standard you set for yourself.\n"
            "You choose peace. You choose abundance. You choose you.\n\n"
            "What standard are you setting for yourself today? 💫"
        ),
        (
            "The version of you that has everything? She exists. 🌹\n\n"
            "She woke up and chose herself first.\n"
            "She stopped shrinking and started expanding.\n"
            "She built the life, not waited for it.\n\n"
            "What's one thing she does that you haven't started yet? ✨"
        ),
        (
            "Luxury is a mindset before it's a lifestyle. 🥂\n\n"
            "You don't need more money. You need to stop tolerating less.\n"
            "Protect your energy. Elevate your standards. Move in silence.\n\n"
            "What are you no longer accepting in your life? 👇"
        ),
        (
            "The glow up isn't just physical. 🌸\n\n"
            "It's choosing stillness over stress.\n"
            "It's saying no without guilt.\n"
            "It's building something quietly — then letting it speak loudly.\n\n"
            "Which part of your glow up are you most proud of? 💬"
        ),
        (
            "She didn't find her confidence. She built it. 🔥\n\n"
            "One boundary at a time. One choice at a time. One day at a time.\n"
            "The soft life is the disciplined life in disguise.\n\n"
            "What did you build today that your future self will thank you for? ✨"
        ),
        (
            "Stop waiting for a sign. This is it. 🌙\n\n"
            "The business. The move. The boundary. The dream.\n"
            "Successful women don't wait for perfect — they move in faith.\n\n"
            "What have you been putting off that you're starting today? 👇"
        ),
        (
            "Your standards aren't too high. Their effort was too low. 💅\n\n"
            "Soft life energy means knowing your worth before anyone else does.\n"
            "You don't negotiate with people who don't see your value.\n\n"
            "Drop a 👑 if you've finally stopped explaining your worth."
        ),
        (
            "The most attractive thing? A woman who knows exactly who she is. ✨\n\n"
            "Unbothered. Intentional. Focused.\n"
            "She's not competing — she's creating.\n\n"
            "What are you creating this season? Tell me below 👇"
        ),
    ]
    HASHTAGS = (
        "HASHTAGS: #LuxuryLifestyle #SoftLifeEra #HighValueWoman #MindsetShift "
        "#BecomingHer #SelfActualisation #EmpoweredLiving #GlowUp "
        "#SoftLifeSeason #PersonalGrowth #FeminineEnergy #LevelUp"
    )

    # Check if today's brief was already generated
    engine = get_engine()
    today = date.today()
    with engine.begin() as conn:
        existing = conn.execute(
            sa_text(
                "SELECT page_index FROM canva_post_schedule "
                "WHERE design_id = :did AND scheduled_date = :d AND status = 'exported'"
            ),
            {"did": DESIGN_ID, "d": today},
        ).fetchone()

    if existing:
        print(f"[BRIEF] Today's brief already exported — page #{existing[0]}. Skipping.")
        return

    # Try full AI brief first, fall back to bypass
    canva = CanvaClient(access_token=settings.canva_access_token, settings=settings)
    try:
        engine_obj = ContentEngine()
        brief = engine_obj.generate_daily_brief(design_id=DESIGN_ID)
        caption = brief.caption
        hashtags = brief.hashtags
        page_idx = brief.page_index
        thumb_url = brief.thumbnail_url
        print(f"[BRIEF] AI brief generated — page #{page_idx}")
    except Exception as e:
        print(f"[BRIEF] AI brief failed ({e}), using bypass mode.")
        # Fetch available pages from Canva
        pages_data = canva._request("GET", f"/designs/{DESIGN_ID}/pages", params={"limit": 50})
        available = {p["index"]: p for p in pages_data.get("items", [])}

        # Get unused pages
        with engine.begin() as conn:
            used = {
                row[0]
                for row in conn.execute(
                    sa_text(
                        "SELECT page_index FROM canva_post_schedule "
                        "WHERE design_id = :did AND status != 'reset'"
                    ),
                    {"did": DESIGN_ID},
                ).fetchall()
            }
        unused = sorted(set(available.keys()) - used) or sorted(available.keys())
        page_idx = random.choice(unused)
        page = available[page_idx]
        thumb_url = page.get("thumbnail", {}).get("url", "")
        caption = random.choice(BYPASS_CAPTIONS)
        hashtags = HASHTAGS

    # Export MP4
    try:
        out = canva.export_design(
            design_id=DESIGN_ID,
            export_format="mp4",
            output_dir=Path("exports"),
            pages=[page_idx],
        )
        caption_file = out.with_suffix(".txt")
        caption_file.write_text(f"CAPTION:\n{caption}\n\n{hashtags}\n", encoding="utf-8")
        print(f"[BRIEF] Exported: {out}")
        print(f"[BRIEF] Caption: {caption_file}")
    except Exception as e:
        print(f"[BRIEF] MP4 export failed ({e}). Brief still saved.")
        out = Path(f"exports/{DESIGN_ID}_p{page_idx}.mp4")

    # Save to schedule DB — mark 'exported' so it is never picked again
    with engine.begin() as conn:
        conn.execute(
            sa_text("""
                INSERT INTO canva_post_schedule
                  (design_id, page_index, scheduled_date, caption, hashtags, thumbnail_url, status)
                VALUES (:did, :idx, :sdate, :caption, :hashtags, :thumb, 'exported')
                ON CONFLICT (design_id, page_index) DO UPDATE SET
                  scheduled_date = EXCLUDED.scheduled_date,
                  caption = EXCLUDED.caption,
                  hashtags = EXCLUDED.hashtags,
                  status = 'exported'
            """),
            {"did": DESIGN_ID, "idx": page_idx, "sdate": today,
             "caption": caption, "hashtags": hashtags, "thumb": thumb_url},
        )

    print(f"\n[BRIEF] ══════════════════════════════════════")
    print(f"[BRIEF]   TODAY'S REEL: page #{page_idx}")
    print(f"[BRIEF]   MP4: {out}")
    print(f"[BRIEF] ══════════════════════════════════════")


def _today_in_timezone(tz_name: str):
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return datetime.now().date()


def _upsert_post(conn, post: FetchedPost) -> None:
    conn.execute(
        text(
            """
            INSERT INTO posts (
              post_id, posted_at, caption, hashtags, audio_name, duration_seconds,
              category, format_type, hook_text, cta_type, visual_style
            )
            VALUES (
              :post_id, :posted_at, :caption, :hashtags, :audio_name, :duration_seconds,
              :category, :format_type, :hook_text, :cta_type, :visual_style
            )
            ON CONFLICT (post_id) DO UPDATE SET
              posted_at = EXCLUDED.posted_at,
              caption = EXCLUDED.caption,
              hashtags = EXCLUDED.hashtags,
              audio_name = EXCLUDED.audio_name,
              duration_seconds = EXCLUDED.duration_seconds,
              category = EXCLUDED.category,
              format_type = EXCLUDED.format_type,
              hook_text = EXCLUDED.hook_text,
              cta_type = EXCLUDED.cta_type,
              visual_style = EXCLUDED.visual_style
            """
        ),
        post.__dict__,
    )


def _upsert_metric(conn, metric: FetchedMetrics, snapshot_date) -> None:
    conn.execute(
        text(
            """
            INSERT INTO post_metrics_daily (
              post_id, snapshot_date, views, likes, comments, shares, saves,
              avg_watch_time_seconds, completion_rate
            )
            VALUES (
              :post_id, :snapshot_date, :views, :likes, :comments, :shares, :saves,
              :avg_watch_time_seconds, :completion_rate
            )
            ON CONFLICT (post_id, snapshot_date) DO UPDATE SET
              views = EXCLUDED.views,
              likes = EXCLUDED.likes,
              comments = EXCLUDED.comments,
              shares = EXCLUDED.shares,
              saves = EXCLUDED.saves,
              avg_watch_time_seconds = EXCLUDED.avg_watch_time_seconds,
              completion_rate = EXCLUDED.completion_rate
            """
        ),
        {**metric.__dict__, "snapshot_date": snapshot_date},
    )


def _log_kpis(post: FetchedPost, metrics: FetchedMetrics) -> None:
    duration = post.duration_seconds or 0
    kpi_engagement = engagement_rate(
        likes=metrics.likes,
        comments=metrics.comments,
        shares=metrics.shares,
        saves=metrics.saves or 0,
        views=metrics.views,
    )
    kpi_share = share_rate(metrics.shares, metrics.views)
    kpi_comment = comment_rate(metrics.comments, metrics.views)
    kpi_retention = retention_proxy(metrics.avg_watch_time_seconds or 0.0, duration)

    print(
        f"[KPI] {post.post_id} engagement={kpi_engagement:.4f} share={kpi_share:.4f} "
        f"comment={kpi_comment:.4f} retention_proxy={kpi_retention:.4f}"
    )
