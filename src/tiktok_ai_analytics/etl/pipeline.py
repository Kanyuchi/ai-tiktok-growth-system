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
