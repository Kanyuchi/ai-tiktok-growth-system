from __future__ import annotations

from pathlib import Path


def _format_value(value: str) -> str:
    escaped = value.replace('"', '\\"')
    if any(ch in value for ch in [" ", "#", "\t"]):
        return f'"{escaped}"'
    return escaped


def upsert_env_values(values: dict[str, str], env_path: str | Path = ".env") -> None:
    path = Path(env_path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    touched: set[str] = set()
    out_lines: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in raw:
            out_lines.append(raw)
            continue

        key, _ = raw.split("=", 1)
        key = key.strip()
        if key in values:
            out_lines.append(f"{key}={_format_value(values[key])}")
            touched.add(key)
        else:
            out_lines.append(raw)

    for key, value in values.items():
        if key not in touched:
            out_lines.append(f"{key}={_format_value(value)}")

    path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")
