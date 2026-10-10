"""SQLite storage: the schema, and one connection per request."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    nickname      TEXT    UNIQUE COLLATE NOCASE,
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'editor')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    # One connection per request; FastAPI may hand it between threads.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(path: Path) -> None:
    """Create the tables if they do not exist yet. Safe to call every start."""
    with closing(connect(path)) as conn:
        conn.executescript(SCHEMA)
