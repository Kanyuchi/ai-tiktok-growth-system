from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tiktok_ai_analytics.cli import run_daily


if __name__ == "__main__":
    run_daily()
