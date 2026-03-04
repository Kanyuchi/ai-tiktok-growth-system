from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tiktok_ai_analytics.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
