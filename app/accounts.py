"""Accounts: who people are, and proving it with a password.

Passwords are stored only as argon2 hashes and are never logged.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app import db

_hasher = PasswordHasher()


@dataclass(frozen=True)
class User:
    id: int
    email: str
    nickname: str | None
    role: str
    active: bool

    @property
    def is_leader(self) -> bool:
        return self.role == "admin"


def _user_from_row(row: sqlite3.Row) -> User:
    return User(id=row["id"], email=row["email"], nickname=row["nickname"],
                role=row["role"], active=bool(row["active"]))


def create_user(conn: sqlite3.Connection, *, email: str, password: str, role: str,
                nickname: str | None = None, active: bool = True) -> User:
    now = db.now()
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, nickname, role, active,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email.strip(), _hasher.hash(password), nickname, role, int(active), now, now),
        )
    user = get_user(conn, cursor.lastrowid)
    assert user is not None
    return user


def get_user(conn: sqlite3.Connection, user_id: int | None) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_from_row(row) if row else None


def active_user(conn: sqlite3.Connection, user_id: int | None) -> User | None:
    """The user a session belongs to, or None once their account is inactive."""
    user = get_user(conn, user_id)
    return user if user and user.active else None


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> User | None:
    """The active user with this email and password, or None."""
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()
    if row is None or not row["active"]:
        return None
    try:
        _hasher.verify(row["password_hash"], password)
    except (VerificationError, InvalidHashError):
        return None
    return _user_from_row(row)


def list_users(conn: sqlite3.Connection) -> list[User]:
    """Every account, the leader's first, then by email."""
    rows = conn.execute("SELECT * FROM users ORDER BY role = 'admin' DESC, email").fetchall()
    return [_user_from_row(row) for row in rows]
