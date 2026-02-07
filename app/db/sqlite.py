import os
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    return os.getenv("RECIPE_DB_PATH", "data/recipes.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    db_path = Path(get_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                recipe_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                recipe_id TEXT NOT NULL,
                note_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(recipe_id) REFERENCES recipes(id)
            )
            """
        )
