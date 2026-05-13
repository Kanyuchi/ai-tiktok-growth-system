from __future__ import annotations

"""
AI caption generator for local videos.

Workflow:
  1. ffmpeg extracts N frames evenly distributed across the video
  2. Frames are encoded as base64 and sent to Claude Sonnet 4.6 with vision
  3. Claude returns N caption variants, each with a hook + body + hashtags
  4. Caller picks one for post-local

Used by the `caption-video` CLI command. Profile-aware via the per-profile
profile.md note (niche description).
"""

import base64
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_FRAMES = 4
DEFAULT_VARIANTS = 3


@dataclass
class CaptionVariant:
    hook: str
    body: str
    hashtags: str  # space-separated, includes the #

    def to_post_caption(self) -> str:
        """The full caption string to feed into post-local."""
        return f"{self.hook}\n\n{self.body}\n\n{self.hashtags}".strip()


@dataclass
class CaptionResult:
    variants: list[CaptionVariant]
    raw_video_summary: str  # what Claude saw, for debugging


def _extract_frames(video_path: Path, n_frames: int, out_dir: Path) -> list[Path]:
    """Extract n_frames evenly spaced frames from a video using ffmpeg."""
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())

    frames: list[Path] = []
    for i in range(n_frames):
        ts = duration * (i + 0.5) / n_frames
        out = out_dir / f"frame_{i:02d}.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", "scale=1024:-1",
                "-q:v", "4",
                str(out),
            ],
            check=True,
        )
        frames.append(out)
    return frames


def _encode_image(path: Path) -> dict:
    """Return an Anthropic-message image block from a local file."""
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": data,
        },
    }


PROMPT_TEMPLATE = """You are writing TikTok captions for the account @{handle}.

Niche: {niche}

I will show you {n_frames} frames sampled evenly from a single video. Treat
them as a sequence (frame 1 = early, frame {n_frames} = late). Based on what
you see, generate exactly {n_variants} distinct caption variants for posting
this video to TikTok.

Caption-writing rules:
- Hook (first line): 6-10 words max. Designed to stop the scroll in the first
  2 seconds. Curiosity, contrast, or a surprising specificity beats hype.
- Body: 1-3 short lines. Conversational, not marketing-speak. No emojis in the
  hook; sparing emojis in the body are fine if they fit the niche.
- Hashtags: 5-10 tags. Mix of high-volume (e.g. #fyp, #foryou) and niche-specific
  tags relevant to what's IN the video. Include at least 2 niche tags.
- Each variant should explore a DIFFERENT angle — e.g. one informational, one
  emotional, one playful. Do not produce three near-duplicates.
- No quotation marks around the caption text.
- Do not number the variants in the caption text itself.

Return JSON only, no prose, no markdown fences, matching this schema exactly:
{{
  "video_summary": "1-2 sentence description of what's in the video for my reference",
  "variants": [
    {{"hook": "...", "body": "...", "hashtags": "#tag1 #tag2 ..."}},
    ...
  ]
}}
"""


def generate_captions(
    video_path: Path,
    handle: str,
    niche: str,
    *,
    n_frames: int = DEFAULT_FRAMES,
    n_variants: int = DEFAULT_VARIANTS,
    api_key: str | None = None,
    model: str = CLAUDE_MODEL,
) -> CaptionResult:
    """Extract frames, call Claude vision, return parsed caption variants."""
    from anthropic import Anthropic

    if not video_path.exists():
        raise FileNotFoundError(video_path)
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory(prefix="tiktok_frames_") as tmp:
        frames = _extract_frames(video_path, n_frames, Path(tmp))
        image_blocks = [_encode_image(p) for p in frames]

        prompt = PROMPT_TEMPLATE.format(
            handle=handle,
            niche=niche,
            n_frames=n_frames,
            n_variants=n_variants,
        )

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": image_blocks + [{"type": "text", "text": prompt}],
                }
            ],
        )

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    parsed = json.loads(text.strip())

    variants = [
        CaptionVariant(
            hook=v["hook"].strip(),
            body=v["body"].strip(),
            hashtags=v["hashtags"].strip(),
        )
        for v in parsed["variants"]
    ]
    return CaptionResult(
        variants=variants,
        raw_video_summary=parsed.get("video_summary", ""),
    )


def load_profile_niche(profile: str | None) -> str:
    """Read the niche line from data/<profile>/profile.md, fallback to env."""
    if profile:
        notes = Path("data") / profile / "profile.md"
        if notes.exists():
            for line in notes.read_text(encoding="utf-8").splitlines():
                if line.startswith("**Niche:**"):
                    return line.replace("**Niche:**", "").strip()
    return os.environ.get("TIKTOK_NICHE", "general lifestyle")
