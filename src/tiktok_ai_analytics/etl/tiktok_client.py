from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

from ..config import Settings, load_settings


class TikTokApiError(RuntimeError):
    pass


@dataclass
class FetchedPost:
    post_id: str
    posted_at: datetime | None
    caption: str | None
    hashtags: str | None
    audio_name: str | None
    duration_seconds: int | None
    category: str | None
    format_type: str | None
    hook_text: str | None
    cta_type: str | None
    visual_style: str | None


@dataclass
class FetchedMetrics:
    post_id: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int | None
    avg_watch_time_seconds: float | None
    completion_rate: float | None


class TikTokClient:
    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.access_token = access_token
        self.base_url = self.settings.tiktok_api_base_url.rstrip("/")
        self.session = requests.Session()

    def list_all_videos(self, max_results: int | None = None) -> list[dict]:
        max_results = max_results or self.settings.tiktok_max_videos_per_run
        cursor = 0
        videos: list[dict] = []

        while len(videos) < max_results:
            page = self._list_videos_page(cursor=cursor, max_count=min(self.settings.tiktok_page_size, 20))
            page_videos = page.get("videos", [])
            if not page_videos:
                break

            videos.extend(page_videos)
            if not page.get("has_more"):
                break

            cursor = int(page.get("cursor", cursor + len(page_videos)))

        return videos[:max_results]

    def query_videos(self, video_ids: list[str]) -> dict[str, dict]:
        if not video_ids:
            return {}

        out: dict[str, dict] = {}
        for i in range(0, len(video_ids), 20):
            chunk = video_ids[i : i + 20]
            payload = {"filters": {"video_ids": chunk}}
            params = {
                "fields": "id,create_time,duration,title,video_description,view_count,like_count,comment_count,share_count"
            }
            body = self._request(
                method="POST",
                endpoint="/video/query/",
                params=params,
                json=payload,
            )
            for item in body.get("data", {}).get("videos", []):
                item_id = item.get("id")
                if item_id:
                    out[item_id] = item

        return out

    def fetch_posts_and_metrics(self, max_videos: int | None = None) -> tuple[list[FetchedPost], list[FetchedMetrics]]:
        videos = self.list_all_videos(max_results=max_videos)
        video_ids = [v.get("id") for v in videos if v.get("id")]
        query_data: dict[str, dict] = {}
        try:
            query_data = self.query_videos(video_ids)
        except TikTokApiError as exc:
            # Some apps can list videos but are not approved for all insights fields yet.
            print(f"[WARN] video/query failed, falling back to list-only fields: {exc}")

        posts: list[FetchedPost] = []
        metrics: list[FetchedMetrics] = []

        for video in videos:
            post_id = video.get("id")
            if not post_id:
                continue

            merged = {**video, **query_data.get(post_id, {})}
            caption = (merged.get("video_description") or merged.get("title") or "").strip() or None
            duration_seconds = self._to_int(merged.get("duration"))

            posts.append(
                FetchedPost(
                    post_id=post_id,
                    posted_at=self._to_datetime(merged.get("create_time")),
                    caption=caption,
                    hashtags=self._extract_hashtags(caption),
                    audio_name=None,
                    duration_seconds=duration_seconds,
                    category=None,
                    format_type=self._infer_format_type(caption),
                    hook_text=self._extract_hook(caption),
                    cta_type=self._infer_cta(caption),
                    visual_style=None,
                )
            )

            metrics.append(
                FetchedMetrics(
                    post_id=post_id,
                    views=self._to_int(merged.get("view_count")) or 0,
                    likes=self._to_int(merged.get("like_count")) or 0,
                    comments=self._to_int(merged.get("comment_count")) or 0,
                    shares=self._to_int(merged.get("share_count")) or 0,
                    saves=self._to_int(merged.get("favorite_count") or merged.get("collect_count")),
                    avg_watch_time_seconds=self._to_float(merged.get("average_watch_duration")),
                    completion_rate=self._to_float(merged.get("completion_rate")),
                )
            )

        return posts, metrics

    def _list_videos_page(self, cursor: int = 0, max_count: int = 20) -> dict:
        params = {
            "fields": "id,create_time,duration,title,video_description",
            "cursor": cursor,
            "max_count": max_count,
        }
        body = self._request(method="POST", endpoint="/video/list/", params=params, json={})
        return body.get("data", {})

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | None = None,
    ) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                timeout=self.settings.tiktok_request_timeout_seconds,
            )

            if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(1.5 * (2**attempt))
                continue

            if response.status_code >= 400:
                raise TikTokApiError(
                    f"TikTok API request failed ({response.status_code}) endpoint={endpoint} body={response.text}"
                )

            payload = response.json()
            error = payload.get("error")
            if error and str(error.get("code", "ok")) not in {"ok", "0"}:
                raise TikTokApiError(f"TikTok API error endpoint={endpoint}: {error}")
            return payload

        raise TikTokApiError(f"TikTok API retries exhausted for endpoint={endpoint}")

    @staticmethod
    def _to_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_datetime(value: object) -> datetime | None:
        raw = TikTokClient._to_int(value)
        if raw is None:
            return None
        return datetime.fromtimestamp(raw, tz=UTC)

    @staticmethod
    def _extract_hashtags(caption: str | None) -> str | None:
        if not caption:
            return None
        tags = [word for word in caption.split() if word.startswith("#")]
        return " ".join(tags) if tags else None

    @staticmethod
    def _infer_format_type(caption: str | None) -> str | None:
        if not caption:
            return None
        lowered = caption.lower()
        if "pov" in lowered:
            return "pov"
        if "how to" in lowered:
            return "instructional"
        return None

    @staticmethod
    def _extract_hook(caption: str | None) -> str | None:
        if not caption:
            return None
        parts = [p.strip() for p in caption.replace("\n", " ").split(".") if p.strip()]
        return parts[0][:140] if parts else caption[:140]

    @staticmethod
    def _infer_cta(caption: str | None) -> str | None:
        if not caption:
            return None
        lowered = caption.lower()
        if "comment" in lowered:
            return "comment"
        if "follow" in lowered:
            return "follow"
        if "share" in lowered:
            return "share"
        if "save" in lowered:
            return "save"
        return None
