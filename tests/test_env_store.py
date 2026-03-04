from pathlib import Path

from tiktok_ai_analytics.env_store import upsert_env_values


def test_upsert_env_values_updates_and_appends(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\nB=2\n", encoding="utf-8")

    upsert_env_values({"B": "20", "C": "3"}, env_file)

    content = env_file.read_text(encoding="utf-8")
    assert "A=1" in content
    assert "B=20" in content
    assert "C=3" in content
