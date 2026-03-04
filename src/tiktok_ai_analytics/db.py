from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import load_settings


def get_engine() -> Engine:
    return create_engine(load_settings().database_url, future=True)


def initialize_schema(schema_path: str | Path = "sql/schema.sql") -> None:
    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as conn:
        for statement in schema_sql.split(";"):
            sql = statement.strip()
            if sql:
                conn.execute(text(sql))
