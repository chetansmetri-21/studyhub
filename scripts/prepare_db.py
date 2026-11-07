import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "studyhub.db"


def get_sqlite_path() -> Path | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return DEFAULT_DB

    if not database_url.startswith("sqlite:///"):
        return None

    sqlite_path = database_url.replace("sqlite:///", "", 1)
    return Path(sqlite_path).resolve() if sqlite_path else DEFAULT_DB


def ensure_alembic_stamp() -> None:
    db_path = get_sqlite_path()
    if db_path is None or not db_path.exists():
        return

    with sqlite3.connect(db_path) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]

        if not tables or "alembic_version" in tables:
            return

        conn.execute(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
        )
        conn.execute(
            "INSERT OR IGNORE INTO alembic_version (version_num) VALUES ('c7f1fd77f9ac')"
        )


if __name__ == "__main__":
    ensure_alembic_stamp()
