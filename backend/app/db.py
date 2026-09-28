from pathlib import Path

from sqlalchemy import create_engine, text

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def apply_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_PATH.read_text()))
