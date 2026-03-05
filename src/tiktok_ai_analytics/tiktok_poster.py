from __future__ import annotations

"""
TikTok Content Posting API client
==================================
Implements TikTok's /v2/post/publish/video/init/ direct upload flow.

Required scope: video.publish
"""

import math
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import Settings, load_settings


class TikTokPostError(RuntimeError):
    pass


@dataclass
class PublishResult:
    publish_id: str
    status: str  # "PUBLISH_COMPLETE", "PROCESSING_DOWNLOAD", etc.
    tiktok_post_url: str | None = None


class TikTokPoster:
    BASE_URL = "https://open.tiktokapis.com/v2"
    CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks

    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or load_settings()
        self.session = requests.Session()

    # ── Public API ────────────────────────────────────────────────────────────

    def post_video(
        self,
        video_path: Path,
        caption: str,
        *,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
    ) -> PublishResult:
        """
        Upload and publish a local video file to TikTok.

        Steps:
          1. Init publish → get upload_url + publish_id
          2. Upload video in chunks
          3. Poll for publish status
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise TikTokPostError(f"Video file not found: {video_path}")

        video_size = video_path.stat().st_size
        total_chunks = math.ceil(video_size / self.CHUNK_SIZE)

        # 1. Init publish
        print(f"[POSTER] Initialising TikTok publish ({video_size:,} bytes, {total_chunks} chunk(s))...")
        init_resp = self._init_publish(
            video_size=video_size,
            caption=caption,
            privacy_level=privacy_level,
            disable_duet=disable_duet,
            disable_comment=disable_comment,
            disable_stitch=disable_stitch,
        )
        publish_id = init_resp["data"]["publish_id"]
        upload_url = init_resp["data"]["upload_url"]
        print(f"[POSTER] publish_id={publish_id}")

        # 2. Upload
        self._upload_chunks(video_path, upload_url, video_size, total_chunks)

        # 3. Poll status
        result = self._poll_status(publish_id)
        print(f"[POSTER] Final status: {result.status}")
        return result

    # ── TikTok API calls ──────────────────────────────────────────────────────

    def _init_publish(
        self,
        video_size: int,
        caption: str,
        privacy_level: str,
        disable_duet: bool,
        disable_comment: bool,
        disable_stitch: bool,
    ) -> dict:
        payload = {
            "post_info": {
                "title": caption[:2200],  # TikTok caption limit
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": min(self.CHUNK_SIZE, video_size),
                "total_chunk_count": math.ceil(video_size / self.CHUNK_SIZE),
            },
        }
        return self._request("POST", "/post/publish/video/init/", json=payload)

    def _upload_chunks(
        self, video_path: Path, upload_url: str, video_size: int, total_chunks: int
    ) -> None:
        with open(video_path, "rb") as f:
            for chunk_idx in range(total_chunks):
                start = chunk_idx * self.CHUNK_SIZE
                end = min(start + self.CHUNK_SIZE, video_size) - 1
                chunk = f.read(self.CHUNK_SIZE)
                content_range = f"bytes {start}-{end}/{video_size}"

                print(f"[POSTER] Uploading chunk {chunk_idx + 1}/{total_chunks} ({content_range})")
                resp = self.session.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": content_range,
                        "Content-Length": str(len(chunk)),
                    },
                    data=chunk,
                    timeout=120,
                )
                if resp.status_code not in {200, 201, 206}:
                    raise TikTokPostError(
                        f"Upload chunk {chunk_idx} failed ({resp.status_code}): {resp.text[:300]}"
                    )
        print("[POSTER] Upload complete.")

    def _poll_status(self, publish_id: str, max_wait: int = 120) -> PublishResult:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            body = self._request("POST", "/post/publish/status/fetch/", json={"publish_id": publish_id})
            data = body.get("data", {})
            status = data.get("status", "UNKNOWN")
            print(f"[POSTER] Status: {status}")

            if status == "PUBLISH_COMPLETE":
                return PublishResult(
                    publish_id=publish_id,
                    status=status,
                )
            if status in {"FAILED", "CANCELLED"}:
                err = data.get("fail_reason", "unknown")
                raise TikTokPostError(f"Publish failed: {err}")

            time.sleep(5)

        raise TikTokPostError(f"Publish timed out after {max_wait}s for publish_id={publish_id}")

    # ── HTTP helper ───────────────────────────────────────────────────────────

    def _request(self, method: str, endpoint: str, *, json: dict | None = None) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        resp = self.session.request(method, url, headers=headers, json=json, timeout=30)
        if resp.status_code >= 400:
            raise TikTokPostError(
                f"TikTok API {method} {endpoint} failed ({resp.status_code}): {resp.text[:500]}"
            )
        body = resp.json()
        # TikTok wraps errors inside the body even on 200
        err = body.get("error", {})
        if err.get("code") and err["code"] != "ok":
            raise TikTokPostError(f"TikTok API error: {err}")
        return body
