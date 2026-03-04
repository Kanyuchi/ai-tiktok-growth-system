from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path

import requests

from .config import Settings, load_settings


class CanvaApiError(RuntimeError):
    pass


@dataclass
class CanvaDesign:
    design_id: str
    title: str
    created_at: datetime | None
    updated_at: datetime | None
    thumbnail_url: str | None
    view_url: str | None
    edit_url: str | None


class CanvaClient:
    BASE_URL = "https://api.canva.com/rest/v1"

    def __init__(self, access_token: str, settings: Settings | None = None) -> None:
        self.access_token = access_token
        self.settings = settings or load_settings()
        self.session = requests.Session()

    # ── Designs ───────────────────────────────────────────────────────────────

    def list_designs(self, query: str | None = None, limit: int = 50) -> list[CanvaDesign]:
        """List designs from the user's Canva account."""
        params: dict = {"limit": min(limit, 50)}
        if query:
            params["query"] = query

        designs: list[CanvaDesign] = []
        continuation = None

        while True:
            if continuation:
                params["continuation"] = continuation
            body = self._request("GET", "/designs", params=params)
            items = body.get("items", [])
            for item in items:
                designs.append(self._parse_design(item))
            continuation = body.get("continuation")
            if not continuation or len(designs) >= limit:
                break

        return designs[:limit]

    def get_design(self, design_id: str) -> CanvaDesign:
        body = self._request("GET", f"/designs/{design_id}")
        return self._parse_design(body.get("design", body))

    def export_design(
        self,
        design_id: str,
        export_format: str = "mp4",
        output_dir: Path | str = ".",
    ) -> Path:
        """
        Create an export job for a design and download the result.
        Supported formats: mp4, gif, jpg, png, pdf
        Returns the path to the downloaded file.
        """
        payload = {
            "design_id": design_id,
            "format": {"type": export_format},
        }
        job = self._request("POST", "/exports", json=payload)
        job_id = job.get("job", {}).get("id")
        if not job_id:
            raise CanvaApiError(f"Export job creation failed: {job}")

        # Poll until done
        for _ in range(60):
            status = self._request("GET", f"/exports/{job_id}")
            job_data = status.get("job", {})
            state = job_data.get("status")
            if state == "success":
                urls = job_data.get("urls", [])
                if not urls:
                    raise CanvaApiError("Export succeeded but no download URLs returned")
                download_url = urls[0]
                return self._download_file(download_url, design_id, export_format, Path(output_dir))
            elif state == "failed":
                raise CanvaApiError(f"Export job failed: {job_data.get('error')}")
            time.sleep(3)

        raise CanvaApiError(f"Export job timed out for design {design_id}")

    # ── Assets ────────────────────────────────────────────────────────────────

    def list_assets(self, limit: int = 50) -> list[dict]:
        params = {"limit": min(limit, 50)}
        body = self._request("GET", "/assets", params=params)
        return body.get("items", [])

    # ── Internals ─────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        for attempt in range(4):
            resp = self.session.request(
                method, url, headers=headers, params=params, json=json, timeout=30
            )
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                raise CanvaApiError(
                    f"Canva API {method} {endpoint} failed ({resp.status_code}): {resp.text}"
                )
            return resp.json()
        raise CanvaApiError(f"Canva API retries exhausted for {endpoint}")

    def _download_file(self, url: str, design_id: str, fmt: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{design_id}.{fmt}"
        dest = output_dir / filename
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return dest

    @staticmethod
    def _parse_design(item: dict) -> CanvaDesign:
        urls = item.get("urls", {})
        return CanvaDesign(
            design_id=item.get("id", ""),
            title=item.get("title", "Untitled"),
            created_at=_ts(item.get("created_at")),
            updated_at=_ts(item.get("updated_at")),
            thumbnail_url=item.get("thumbnail", {}).get("url"),
            view_url=urls.get("view_url"),
            edit_url=urls.get("edit_url"),
        )


def _ts(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)
