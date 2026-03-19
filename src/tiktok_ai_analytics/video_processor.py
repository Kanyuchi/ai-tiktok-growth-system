"""Burn username overlay onto exported MP4 videos using ffmpeg."""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

FFMPEG_BIN = "/opt/homebrew/bin/ffmpeg"


def add_username_overlay(
    video_path: Path,
    username: str = "@thesoftupgrade1",
    *,
    font: str = "Arial",
    fontsize: int = 42,
    fontcolor: str = "white@0.85",
    shadow_color: str = "black@0.4",
    shadow_x: int = 2,
    shadow_y: int = 2,
    y_ratio: float = 0.82,
) -> Path:
    """Overlay *username* onto *video_path* (bottom-centre) and replace in-place.

    Returns the path to the processed video.  If ffmpeg is missing or the
    encode fails, the original file is returned unchanged.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        logger.warning("Video file not found: %s — skipping overlay", video_path)
        return video_path

    drawtext = (
        f"drawtext=text='{username}':"
        f"fontsize={fontsize}:"
        f"fontcolor={fontcolor}:"
        f"shadowcolor={shadow_color}:"
        f"shadowx={shadow_x}:shadowy={shadow_y}:"
        f"x=(w-text_w)/2:y=h*{y_ratio}:"
        f"font={font}"
    )

    fd, tmp_path = tempfile.mkstemp(suffix=".mp4", dir=video_path.parent)
    os.close(fd)

    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(video_path),
        "-vf", drawtext,
        "-codec:a", "copy",
        "-preset", "fast",
        str(tmp_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        os.replace(tmp_path, video_path)
        logger.info("Username overlay applied: %s", video_path)
    except FileNotFoundError:
        logger.warning("ffmpeg not found at %s — skipping overlay", FFMPEG_BIN)
        _cleanup(tmp_path)
    except subprocess.CalledProcessError as exc:
        logger.warning("ffmpeg overlay failed: %s — keeping original", exc.stderr[:200] if exc.stderr else exc)
        _cleanup(tmp_path)
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg overlay timed out — keeping original")
        _cleanup(tmp_path)

    return video_path


def _cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
